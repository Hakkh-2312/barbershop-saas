from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.whatsapp_conversation import WhatsappConversation
from app.services.billing import is_subscription_active
from app.services.booking import (
    BookingError,
    create_booking,
    get_available_dates,
    get_available_slots,
    reschedule_booking,
)
from app.services.notifications import notify_barber, resolve_phone_number_id
from app.services.reminders import (
    CANCEL_BUTTON_PAYLOAD,
    CANCEL_BUTTON_TITLES,
    cancel_via_reminder_button,
)
from app.services.whatsapp_client import send_whatsapp_interactive_list, send_whatsapp_message
from app.services.whatsapp_i18n import (
    DEFAULT_LANGUAGE,
    TRANSLATIONS,
    format_date_full,
    format_date_row_title,
    t,
)

# WhatsApp list messages cap at 10 rows total; the 10th is reserved for a
# "more options" row when there's a next page.
PAGE_SIZE = 9


def _is_reminder_cancel_button(button_reply: dict) -> bool:
    return (
        button_reply.get("id") == CANCEL_BUTTON_PAYLOAD
        or button_reply.get("title", "").strip() in CANCEL_BUTTON_TITLES
    )


def _send_text(db: Session, conversation: WhatsappConversation, body: str) -> None:
    send_whatsapp_message(
        conversation.phone_number,
        body,
        phone_number_id=resolve_phone_number_id(db, conversation.tenant_id),
    )


def _send_list(
    db: Session,
    conversation: WhatsappConversation,
    header: str,
    body: str,
    button_text: str,
    sections: list[dict],
) -> None:
    send_whatsapp_interactive_list(
        to=conversation.phone_number,
        header=header,
        body=body,
        button_text=button_text,
        sections=sections,
        phone_number_id=resolve_phone_number_id(db, conversation.tenant_id),
    )


def handle_message(
    db: Session,
    tenant_id: int,
    from_number: str,
    message: dict,
    contact_name: str | None,
) -> None:
    conversation = _get_or_create_conversation(db, tenant_id, from_number)

    # Meta can and does redeliver the same webhook event (e.g. if the
    # server was slow to ack) - reprocessing an already-handled tap would
    # re-evaluate it against whatever state the first delivery already
    # moved us into (usually main_menu), which renders something new
    # rather than being a safe no-op. Skip anything we've already seen.
    message_id = message.get("id")
    if message_id and message_id == conversation.last_message_id:
        return
    if message_id:
        conversation.last_message_id = message_id
        db.commit()

    if message.get("type") == "interactive":
        button_reply = message.get("interactive", {}).get("button_reply")
        if button_reply and _is_reminder_cancel_button(button_reply):
            cancelled = cancel_via_reminder_button(db, tenant_id, from_number)
            if cancelled:
                _send_text(db, conversation, t(conversation.language, "appt_cancelled"))
            return

    if conversation.state == "awaiting_name" and message.get("type") == "text":
        name = message.get("text", {}).get("body", "").strip()
        if name:
            _register_customer(db, conversation, name)
        else:
            _render_ask_name(db, conversation)
        return

    selection_id = None
    if message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "list_reply":
            selection_id = interactive["list_reply"]["id"]

    if selection_id:
        if selection_id.startswith("menu:"):
            _handle_menu_selection(db, conversation, selection_id)
            return
        if selection_id.startswith("lang:") and conversation.state == "choosing_language":
            _handle_language_selection(db, conversation, selection_id)
            return
        if (
            selection_id.startswith("appt:")
            and conversation.state == "awaiting_appointment_action"
        ):
            _handle_appointment_action(db, conversation, selection_id)
            return
        if (
            selection_id.startswith(("service:", "more_services:"))
            and conversation.state == "awaiting_service"
        ):
            _handle_service_selection(db, conversation, selection_id)
            return
        if (
            selection_id.startswith(("date:", "more_dates:"))
            and conversation.state == "awaiting_date"
        ):
            _handle_date_selection(db, conversation, selection_id)
            return
        if (
            selection_id.startswith(("slot:", "more_slots:"))
            and conversation.state == "awaiting_slot"
        ):
            _handle_slot_selection(db, conversation, selection_id, contact_name)
            return

    # Anything else (first contact, plain text, a tap on a stale/expired
    # list): re-render whatever the current state is.
    _render_current_state(db, conversation)


def _get_or_create_conversation(
    db: Session, tenant_id: int, phone_number: str
) -> WhatsappConversation:
    conversation = (
        db.query(WhatsappConversation)
        .filter(
            WhatsappConversation.tenant_id == tenant_id,
            WhatsappConversation.phone_number == phone_number,
        )
        .first()
    )

    if conversation:
        return conversation

    conversation = WhatsappConversation(
        tenant_id=tenant_id,
        phone_number=phone_number,
        state="main_menu",
        language=DEFAULT_LANGUAGE,
        page=0,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _paginate(items: list, page: int) -> tuple[list, bool]:
    start = page * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    has_more = start + PAGE_SIZE < len(items)
    return chunk, has_more


def _render_current_state(db: Session, conversation: WhatsappConversation) -> None:
    if conversation.state == "choosing_language":
        _render_language_picker(db, conversation)
    elif conversation.state == "awaiting_service":
        _render_service_list(db, conversation)
    elif conversation.state == "awaiting_date":
        _render_date_list(db, conversation)
    elif conversation.state == "awaiting_slot":
        _render_slot_list(db, conversation)
    elif conversation.state == "awaiting_name":
        _render_ask_name(db, conversation)
    elif conversation.state == "awaiting_appointment_action":
        _render_appointment_action(db, conversation)
    else:
        _render_entry(db, conversation)


def _find_customer(db: Session, tenant_id: int, phone_number: str) -> Customer | None:
    return (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == phone_number)
        .first()
    )


def _find_upcoming_appointment(
    db: Session, tenant_id: int, customer_id: int
) -> Appointment | None:
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.customer_id == customer_id,
            Appointment.status == "booked",
            Appointment.start_time >= datetime.now(),
        )
        .order_by(Appointment.start_time)
        .first()
    )


def _render_entry(db: Session, conversation: WhatsappConversation) -> None:
    """The default landing spot for a message that isn't part of an
    in-progress selection (a fresh "hi", or one that reset back to
    main_menu) - decides whether this is a first-time contact who needs to
    register a name, a returning customer with an upcoming appointment to
    manage, or just the normal main menu."""
    customer = _find_customer(db, conversation.tenant_id, conversation.phone_number)

    if not customer:
        conversation.state = "awaiting_name"
        db.commit()
        _render_ask_name(db, conversation)
        return

    appointment = _find_upcoming_appointment(db, conversation.tenant_id, customer.id)
    if appointment:
        conversation.state = "awaiting_appointment_action"
        conversation.selected_appointment_id = appointment.id
        db.commit()
        _render_appointment_action(db, conversation)
        return

    _render_main_menu(db, conversation)


def _render_ask_name(db: Session, conversation: WhatsappConversation) -> None:
    _send_text(db, conversation, t(conversation.language, "ask_name"))


def _register_customer(db: Session, conversation: WhatsappConversation, name: str) -> None:
    existing = _find_customer(db, conversation.tenant_id, conversation.phone_number)
    if not existing:
        db.add(
            Customer(
                tenant_id=conversation.tenant_id,
                name=name[:255],
                phone=conversation.phone_number,
            )
        )
    conversation.state = "main_menu"
    db.commit()
    _render_entry(db, conversation)


def _render_appointment_action(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == conversation.selected_appointment_id,
            Appointment.tenant_id == conversation.tenant_id,
        )
        .first()
    )
    if not appointment or appointment.status != "booked":
        _show_main_menu(db, conversation)
        return

    service = db.query(Service).filter(Service.id == appointment.service_id).first()

    rows = [
        {"id": "appt:reschedule", "title": t(lang, "appt_reschedule")},
        {"id": "appt:cancel", "title": t(lang, "appt_cancel")},
    ]
    _send_list(
        db,
        conversation,
        header=t(lang, "appt_header"),
        body=t(
            lang,
            "appt_body",
            service_name=service.name if service else "",
            date=format_date_full(lang, appointment.start_time.date()),
            time=appointment.start_time.strftime("%H:%M"),
        ),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "appt_header"), "rows": rows}],
    )


def _handle_appointment_action(
    db: Session, conversation: WhatsappConversation, selection_id: str
) -> None:
    action = selection_id.split(":", 1)[1]
    lang = conversation.language

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == conversation.selected_appointment_id,
            Appointment.tenant_id == conversation.tenant_id,
        )
        .first()
    )
    if not appointment or appointment.status != "booked":
        _show_main_menu(db, conversation)
        return

    if action == "cancel":
        appointment.status = "cancelled"
        db.commit()
        _send_text(db, conversation, t(lang, "appt_cancelled"))

        customer = (
            db.query(Customer)
            .filter(
                Customer.tenant_id == conversation.tenant_id,
                Customer.phone == conversation.phone_number,
            )
            .first()
        )
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        notify_barber(
            db,
            conversation.tenant_id,
            "cancellation",
            "Appointment cancelled",
            f"{customer.name if customer else conversation.phone_number} cancelled "
            f"{service.name if service else 'their appointment'} on "
            f"{appointment.start_time.strftime('%b %d at %H:%M')}.",
            appointment_id=appointment.id,
            customer_name=customer.name if customer else conversation.phone_number,
            service_name=service.name if service else None,
            appointment_time=appointment.start_time,
        )

        # Same as a successful booking: end the conversation here rather
        # than immediately pushing another menu - the customer just asked
        # to cancel, not to see what else they can do right now.
        _reset_to_main_menu(conversation)
        db.commit()
        return

    if action == "reschedule":
        conversation.selected_service_id = appointment.service_id
        conversation.selected_date = None
        conversation.state = "awaiting_date"
        conversation.page = 0
        db.commit()
        _render_date_list(db, conversation)
        return


def _reset_to_main_menu(conversation: WhatsappConversation) -> None:
    """State-only reset, no message sent - used when the conversation
    should just go quiet (e.g. after a successful booking) until the
    customer messages again."""
    conversation.state = "main_menu"
    conversation.page = 0
    conversation.selected_service_id = None
    conversation.selected_date = None
    conversation.selected_appointment_id = None


def _show_main_menu(db: Session, conversation: WhatsappConversation) -> None:
    """Reset and immediately re-render the entry point - used for recovery
    paths (an error, a dead end) where proactively re-offering something is
    more helpful than leaving the customer to message in again. Goes
    through _render_entry (not straight to the main menu) so a customer
    who still has some other upcoming appointment is offered cancel/
    reschedule for it rather than "book" - the same check a fresh message
    would get."""
    _reset_to_main_menu(conversation)
    db.commit()
    _render_entry(db, conversation)


def _render_main_menu(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    tenant = db.query(Tenant).filter(Tenant.id == conversation.tenant_id).first()
    shop_name = tenant.name if tenant else ""

    rows = [
        {"id": "menu:book", "title": t(lang, "menu_book")},
        {"id": "menu:language", "title": t(lang, "menu_language")},
        {"id": "menu:call", "title": t(lang, "menu_call")},
        {"id": "menu:address", "title": t(lang, "menu_address")},
    ]

    _send_list(
        db,
        conversation,
        header=t(lang, "welcome_header"),
        body=t(lang, "welcome_body", shop_name=shop_name),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "welcome_header"), "rows": rows}],
    )


def _handle_menu_selection(
    db: Session, conversation: WhatsappConversation, selection_id: str
) -> None:
    action = selection_id.split(":", 1)[1]
    lang = conversation.language

    if action == "book":
        tenant = db.query(Tenant).filter(Tenant.id == conversation.tenant_id).first()
        if not tenant or not is_subscription_active(tenant):
            _send_text(db, conversation, t(lang, "booking_unavailable"))
            return

        if not _find_customer(db, conversation.tenant_id, conversation.phone_number):
            # Stale button tap from an unregistered number - register their
            # name first rather than letting them book anonymously.
            conversation.state = "awaiting_name"
            db.commit()
            _render_ask_name(db, conversation)
            return

        conversation.state = "awaiting_service"
        conversation.page = 0
        conversation.selected_service_id = None
        conversation.selected_date = None
        db.commit()
        _render_service_list(db, conversation)
        return

    if action == "language":
        conversation.state = "choosing_language"
        db.commit()
        _render_language_picker(db, conversation)
        return

    tenant = db.query(Tenant).filter(Tenant.id == conversation.tenant_id).first()

    if action == "call":
        if tenant and tenant.phone:
            reply = t(lang, "call_reply", phone=tenant.phone)
        else:
            reply = t(lang, "call_not_set")
        _send_text(db, conversation, reply)
        return

    if action == "address":
        if tenant and tenant.address:
            _send_text(db, conversation, t(lang, "address_reply", address=tenant.address))
        else:
            _send_text(db, conversation, t(lang, "address_not_set"))
        return


def _render_language_picker(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    rows = [
        {"id": "lang:ar", "title": t(lang, "lang_ar")},
        {"id": "lang:he", "title": t(lang, "lang_he")},
        {"id": "lang:en", "title": t(lang, "lang_en")},
    ]

    _send_list(
        db,
        conversation,
        header=t(lang, "lang_header"),
        body=t(lang, "lang_body"),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "lang_header"), "rows": rows}],
    )


def _handle_language_selection(
    db: Session, conversation: WhatsappConversation, selection_id: str
) -> None:
    new_language = selection_id.split(":", 1)[1]
    if new_language not in TRANSLATIONS:
        new_language = DEFAULT_LANGUAGE

    conversation.language = new_language
    conversation.state = "main_menu"
    db.commit()
    _render_main_menu(db, conversation)


def _render_service_list(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    services = (
        db.query(Service)
        .filter(Service.tenant_id == conversation.tenant_id)
        .order_by(Service.id)
        .all()
    )

    if not services:
        _send_text(db, conversation, t(lang, "no_services"))
        return

    page_items, has_more = _paginate(services, conversation.page)
    rows = [
        {
            "id": f"service:{s.id}",
            "title": s.name[:24],
            "description": f"{s.duration_minutes} min · {s.price} ₪"[:72],
        }
        for s in page_items
    ]
    if has_more:
        more_id = f"more_services:{conversation.page + 1}"
        rows.append({"id": more_id, "title": t(lang, "more_options")})

    _send_list(
        db,
        conversation,
        header=t(lang, "service_header"),
        body=t(lang, "service_body"),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "service_header"), "rows": rows}],
    )


def _handle_service_selection(
    db: Session, conversation: WhatsappConversation, selection_id: str
) -> None:
    kind, value = selection_id.split(":", 1)

    if kind == "more_services":
        conversation.page = int(value)
        db.commit()
        _render_service_list(db, conversation)
        return

    service = (
        db.query(Service)
        .filter(Service.id == int(value), Service.tenant_id == conversation.tenant_id)
        .first()
    )
    if not service:
        _render_service_list(db, conversation)
        return

    conversation.selected_service_id = service.id
    conversation.state = "awaiting_date"
    conversation.page = 0
    db.commit()
    _render_date_list(db, conversation)


def _render_date_list(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    service = (
        db.query(Service).filter(Service.id == conversation.selected_service_id).first()
    )
    if not service:
        _show_main_menu(db, conversation)
        return

    dates = get_available_dates(db, conversation.tenant_id, service, start_date=date.today())

    if not dates:
        _send_text(db, conversation, t(lang, "no_dates"))
        _show_main_menu(db, conversation)
        return

    page_items, has_more = _paginate(dates, conversation.page)
    rows = [
        {"id": f"date:{d.isoformat()}", "title": format_date_row_title(lang, d)}
        for d in page_items
    ]
    if has_more:
        rows.append({"id": f"more_dates:{conversation.page + 1}", "title": t(lang, "more_options")})

    _send_list(
        db,
        conversation,
        header=t(lang, "date_header"),
        body=t(lang, "date_body"),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "date_header"), "rows": rows}],
    )


def _handle_date_selection(
    db: Session, conversation: WhatsappConversation, selection_id: str
) -> None:
    kind, value = selection_id.split(":", 1)

    if kind == "more_dates":
        conversation.page = int(value)
        db.commit()
        _render_date_list(db, conversation)
        return

    conversation.selected_date = date.fromisoformat(value)
    conversation.state = "awaiting_slot"
    conversation.page = 0
    db.commit()
    _render_slot_list(db, conversation)


def _render_slot_list(db: Session, conversation: WhatsappConversation) -> None:
    lang = conversation.language
    service = (
        db.query(Service).filter(Service.id == conversation.selected_service_id).first()
    )
    if not service or not conversation.selected_date:
        _show_main_menu(db, conversation)
        return

    slots = get_available_slots(
        db,
        conversation.tenant_id,
        service,
        start_date=conversation.selected_date,
        num_days=1,
        limit=50,
    )

    if not slots:
        _send_text(db, conversation, t(lang, "no_slots"))
        _show_main_menu(db, conversation)
        return

    page_items, has_more = _paginate(slots, conversation.page)
    rows = [{"id": f"slot:{s.isoformat()}", "title": s.strftime("%H:%M")} for s in page_items]
    if has_more:
        rows.append({"id": f"more_slots:{conversation.page + 1}", "title": t(lang, "more_options")})

    _send_list(
        db,
        conversation,
        header=t(lang, "slot_header"),
        body=t(lang, "slot_body", date=format_date_full(lang, conversation.selected_date)),
        button_text=t(lang, "menu_button"),
        sections=[{"title": t(lang, "slot_header"), "rows": rows}],
    )


def _handle_slot_selection(
    db: Session,
    conversation: WhatsappConversation,
    selection_id: str,
    contact_name: str | None,
) -> None:
    kind, value = selection_id.split(":", 1)

    if kind == "more_slots":
        conversation.page = int(value)
        db.commit()
        _render_slot_list(db, conversation)
        return

    lang = conversation.language
    start_time = datetime.fromisoformat(value)

    if conversation.selected_appointment_id:
        _handle_reschedule_slot(db, conversation, start_time)
        return

    customer = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == conversation.tenant_id,
            Customer.phone == conversation.phone_number,
        )
        .first()
    )
    if not customer:
        customer = Customer(
            tenant_id=conversation.tenant_id,
            name=contact_name or conversation.phone_number,
            phone=conversation.phone_number,
        )
        db.add(customer)
        db.flush()

    try:
        appointment = create_booking(
            db,
            conversation.tenant_id,
            customer.id,
            conversation.selected_service_id,
            start_time,
        )
    except BookingError as err:
        if err.code == "conflict":
            _send_text(db, conversation, t(lang, "booking_conflict"))
        else:
            _send_text(db, conversation, t(lang, "booking_error"))
        _show_main_menu(db, conversation)
        return

    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == conversation.tenant_id).first()

    _send_text(
        db,
        conversation,
        t(
            lang,
            "booking_summary",
            shop_name=tenant.name if tenant else "",
            service_name=service.name if service else "",
            price=service.price if service else "",
            date=format_date_full(lang, appointment.start_time.date()),
            time=appointment.start_time.strftime("%H:%M"),
        ),
    )
    notify_barber(
        db,
        conversation.tenant_id,
        "new_booking",
        "New booking",
        f"{customer.name} booked {service.name if service else 'an appointment'} on "
        f"{appointment.start_time.strftime('%b %d at %H:%M')}.",
        appointment_id=appointment.id,
        customer_name=customer.name,
        service_name=service.name if service else None,
        appointment_time=appointment.start_time,
    )
    # Per spec: the conversation just ends here - no menu re-push. The
    # customer sees it again next time they message in (main_menu is the
    # fallback _render_current_state renders).
    _reset_to_main_menu(conversation)
    db.commit()


def _handle_reschedule_slot(
    db: Session, conversation: WhatsappConversation, start_time: datetime
) -> None:
    lang = conversation.language

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == conversation.selected_appointment_id,
            Appointment.tenant_id == conversation.tenant_id,
        )
        .first()
    )
    if not appointment:
        _show_main_menu(db, conversation)
        return

    try:
        appointment = reschedule_booking(db, conversation.tenant_id, appointment, start_time)
    except BookingError as err:
        if err.code == "conflict":
            _send_text(db, conversation, t(lang, "booking_conflict"))
        else:
            _send_text(db, conversation, t(lang, "booking_error"))
        _show_main_menu(db, conversation)
        return

    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == conversation.tenant_id).first()

    _send_text(
        db,
        conversation,
        t(
            lang,
            "reschedule_summary",
            shop_name=tenant.name if tenant else "",
            service_name=service.name if service else "",
            price=service.price if service else "",
            date=format_date_full(lang, appointment.start_time.date()),
            time=appointment.start_time.strftime("%H:%M"),
        ),
    )

    customer = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == conversation.tenant_id,
            Customer.phone == conversation.phone_number,
        )
        .first()
    )
    notify_barber(
        db,
        conversation.tenant_id,
        "reschedule",
        "Appointment rescheduled",
        f"{customer.name if customer else conversation.phone_number} moved "
        f"{service.name if service else 'their appointment'} to "
        f"{appointment.start_time.strftime('%b %d at %H:%M')}.",
        appointment_id=appointment.id,
        customer_name=customer.name if customer else conversation.phone_number,
        service_name=service.name if service else None,
        appointment_time=appointment.start_time,
    )

    _reset_to_main_menu(conversation)
    db.commit()
