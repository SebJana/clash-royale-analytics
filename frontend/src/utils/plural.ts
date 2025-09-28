export function pluralize(
  amount: number,
  singularOption: string,
  pluralOption: string
): string {
  if (amount === 1) {
    return singularOption;
  }
  if (amount === 0) {
    return pluralOption;
  }
  return pluralOption;
}
