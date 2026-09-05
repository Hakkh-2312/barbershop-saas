/** Builds a wa.me deep link from a customer's phone number.
 *
 * Numbers in the system are free text - some come from the WhatsApp
 * booking flow itself and are already in full international form (e.g.
 * "972501234567"), others are typed into the dashboard by hand and are
 * often local (e.g. "0501234567"). wa.me needs the full international
 * form, so a locally-formatted number (leading 0) gets its 0 replaced
 * with the shop's country code; anything else is assumed to already be
 * international and is passed through untouched. */
export function toWhatsAppLink(phone: string, countryCode: string | null | undefined): string {
  const digits = phone.replace(/\D/g, "");
  const normalized =
    digits.startsWith("0") && countryCode
      ? countryCode.replace(/\D/g, "") + digits.slice(1)
      : digits;
  return `https://wa.me/${normalized}`;
}
