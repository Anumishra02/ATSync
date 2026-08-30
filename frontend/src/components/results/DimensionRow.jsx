import { DIMENSION_BY_KEY } from "@/lib/constants";
import { dimPct, dimTone, dimReason } from "@/lib/results";
import { cn } from "@/lib/utils";

const BAR_COLOR = { ok: "bg-ok", warn: "bg-warn" };
const NUM_COLOR = { ok: "text-ok", warn: "text-warn" };

export default function DimensionRow({ dim }) {
  const meta = DIMENSION_BY_KEY[dim.dimension] || { label: dim.dimension, blurb: "", max: dim.max_points };
  const scored = dim.status === "scored";
  const tone = dimTone(dim);
  const pct = dimPct(dim);

  return (
    <div className="grid grid-cols-[1fr_auto] items-baseline gap-x-6 gap-y-3 py-5">
      <div className="min-w-0">
        <h3 className="text-[15px] font-medium text-ink">{meta.label}</h3>
        <p className={cn("mt-0.5 text-[13px]", scored ? "text-subtle" : "text-absent")}>{meta.blurb}</p>
      </div>

      <div className="text-right font-pixel tabular-nums">
        {scored ? (
          <span className={cn("text-xl", NUM_COLOR[tone])}>
            {trim(dim.score)}
            <span className="text-subtle">/{trim(dim.max_points)}</span>
          </span>
        ) : (
          <span className="text-xl text-absent">— /{trim(dim.max_points)}</span>
        )}
      </div>

      <div className="col-span-2">
        {scored ? (
          <div className="h-1 w-full overflow-hidden rounded-full bg-hairline">
            <div
              className={cn("h-full rounded-full transition-[width] duration-1000 ease-stage", BAR_COLOR[tone])}
              style={{ width: `${Math.max(2, pct * 100)}%` }}
            />
          </div>
        ) : (
          <p className="border-l-2 border-absent/40 pl-3 text-[13px] text-absent">
            <span className="font-pixel text-[11px] uppercase tracking-wider">
              {dim.status === "not_applicable" ? "not applicable" : "uncomputable"}
            </span>
            <span className="mx-2 text-absent/50">·</span>
            {dimReason(dim)}
          </p>
        )}
      </div>
    </div>
  );
}

function trim(n) {
  return Number.isInteger(n) ? n : Number(n).toFixed(1);
}
