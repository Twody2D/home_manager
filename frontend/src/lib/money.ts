// No per-tenant currency setting exists yet — hardcoded for the whole app.
const CURRENCY = "RUB";

export function formatMoney(amount: string | number, locale: string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  return new Intl.NumberFormat(locale, { style: "currency", currency: CURRENCY }).format(value);
}
