/** Score -> hex colour, on a 0–100 scale. Shared by the score ring, the
 *  dimension bars, and the sidebar badges. */
export function scoreColor(s) {
  return s >= 80 ? "#16a34a" : s >= 60 ? "#d97706" : s >= 40 ? "#f97316" : "#dc2626";
}
