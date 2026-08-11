"""Dựng dashboard HTML tĩnh từ data/logs.jsonl theo contract config/dashboard.yaml.

Chạy: python scripts/build_dashboard.py
Kết quả: data/dashboard.html (mở bằng trình duyệt để xem/chụp evidence).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402

PALETTE = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "surface": "#fcfcfb",
    "page": "#f9f9f7",
    "ink_primary": "#0b0b0b",
    "ink_secondary": "#52514e",
    "ink_muted": "#898781",
    "gridline": "#e1e0d9",
    "baseline": "#c3c2b7",
    "good": "#0ca30c",
    "critical": "#d03b3b",
    "border": "rgba(11,11,11,0.10)",
}


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def minute_bucket(ts: datetime) -> str:
    return ts.strftime("%H:%M")


def badge(passed: bool) -> str:
    color = PALETTE["good"] if passed else PALETTE["critical"]
    label = "PASS" if passed else "FAIL"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font:600 11px system-ui;color:{color};border:1px solid {color};'
        f'border-radius:999px;padding:2px 8px;">{label}</span>'
    )


def check_threshold(value: float, threshold: dict) -> bool:
    op = threshold["operator"]
    target = threshold["value"]
    if op == "lte":
        return value <= target
    return value >= target


def bar_chart(items: list[tuple[str, float]], unit: str, color: str, threshold_value: float | None = None) -> str:
    if not items:
        return f'<div style="color:{PALETTE["ink_muted"]};font:13px system-ui;padding:24px 0;">Không có dữ liệu trong khung thời gian.</div>'
    width, height = 420, 140
    pad_left, pad_bottom = 8, 20
    max_val = max(v for _, v in items)
    max_val = max(max_val, threshold_value or 0, 1e-9)
    bar_w = (width - pad_left) / len(items)
    bars = []
    for i, (label, val) in enumerate(items):
        bar_h = (val / max_val) * (height - pad_bottom - 10)
        x = pad_left + i * bar_w + bar_w * 0.15
        w = bar_w * 0.7
        y = height - pad_bottom - bar_h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bar_h:.1f}" rx="4" fill="{color}" />'
            f'<text x="{x + w / 2:.1f}" y="{height - pad_bottom + 12}" text-anchor="middle" '
            f'font-size="10" fill="{PALETTE["ink_muted"]}" font-family="system-ui">{label}</text>'
            f'<text x="{x + w / 2:.1f}" y="{y - 4:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{PALETTE["ink_secondary"]}" font-family="system-ui">{val:g}</text>'
        )
    threshold_line = ""
    if threshold_value is not None:
        ty = height - pad_bottom - (threshold_value / max_val) * (height - pad_bottom - 10)
        threshold_line = (
            f'<line x1="{pad_left}" y1="{ty:.1f}" x2="{width}" y2="{ty:.1f}" '
            f'stroke="{PALETTE["critical"]}" stroke-width="1.5" stroke-dasharray="4 3" />'
            f'<text x="{width - 4}" y="{ty - 4:.1f}" text-anchor="end" font-size="9" '
            f'fill="{PALETTE["critical"]}" font-family="system-ui">nguong {threshold_value:g}{unit}</text>'
        )
    baseline = f'<line x1="{pad_left}" y1="{height - pad_bottom}" x2="{width}" y2="{height - pad_bottom}" stroke="{PALETTE["baseline"]}" stroke-width="1" />'
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">'
        f"{baseline}{''.join(bars)}{threshold_line}</svg>"
    )


def panel_card(title: str, unit: str, value_label: str, passed: bool, chart_html: str, note: str = "") -> str:
    return f"""
    <section style="background:{PALETTE['surface']};border:1px solid {PALETTE['border']};
        border-radius:12px;padding:16px 18px;display:flex;flex-direction:column;gap:8px;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <h2 style="margin:0;font:600 14px system-ui;color:{PALETTE['ink_primary']};">{title}</h2>
        {badge(passed)}
      </div>
      <div style="font:700 22px system-ui;color:{PALETTE['ink_primary']};">{value_label}
        <span style="font:400 12px system-ui;color:{PALETTE['ink_muted']};">{unit}</span></div>
      {chart_html}
      <div style="font:11px system-ui;color:{PALETTE['ink_muted']};">{note}</div>
    </section>
    """


def build(config_path: Path, logs_path: Path, output_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))["dashboard"]
    panels_cfg = {p["id"]: p for p in config["panels"]}
    records = load_records(logs_path)

    responses = [r for r in records if r.get("event") == "response_sent"]
    requests_recv = [r for r in records if r.get("event") == "request_received"]
    failures = [r for r in records if r.get("event") == "request_failed"]

    if records:
        latest_ts = max(parse_ts(r["ts"]) for r in records if "ts" in r)
    else:
        latest_ts = datetime.now(timezone.utc)

    # --- Latency ---
    latencies = [r["latency_ms"] for r in responses if r.get("latency_ms") is not None]
    p50, p95, p99 = percentile(latencies, 50), percentile(latencies, 95), percentile(latencies, 99)
    lat_cfg = panels_cfg["latency"]
    lat_pass = check_threshold(p95, lat_cfg["threshold"])
    lat_chart = bar_chart(
        [("P50", p50), ("P95", p95), ("P99", p99)],
        "ms",
        PALETTE["blue"],
        threshold_value=lat_cfg["threshold"]["value"],
    )

    # --- Traffic ---
    traffic_by_minute: dict[str, int] = defaultdict(int)
    for r in requests_recv:
        traffic_by_minute[minute_bucket(parse_ts(r["ts"]))] += 1
    traffic_items = sorted(traffic_by_minute.items())
    total_requests = len(requests_recv)
    minutes_span = max(len(traffic_items), 1)
    rate_per_minute = round(total_requests / minutes_span, 2)
    traf_cfg = panels_cfg["traffic"]
    traf_pass = check_threshold(rate_per_minute, traf_cfg["threshold"])
    traf_chart = bar_chart(traffic_items, "req", PALETTE["aqua"])

    # --- Errors ---
    error_rate = round((len(failures) / total_requests) * 100, 2) if total_requests else 0.0
    error_breakdown = Counter(r.get("error_type", "unknown") for r in failures)
    err_cfg = panels_cfg["errors"]
    err_pass = check_threshold(error_rate, err_cfg["threshold"])
    err_chart = bar_chart(list(error_breakdown.items()), "count", PALETTE["magenta"])

    # --- Cost ---
    cost_by_minute: dict[str, float] = defaultdict(float)
    for r in responses:
        cost_by_minute[minute_bucket(parse_ts(r["ts"]))] += r.get("cost_usd") or 0.0
    cost_items = sorted((m, round(v, 4)) for m, v in cost_by_minute.items())
    total_cost = round(sum(r.get("cost_usd") or 0.0 for r in responses), 4)
    cost_cfg = panels_cfg["cost"]
    cost_pass = check_threshold(total_cost, cost_cfg["threshold"])
    cost_chart = bar_chart(cost_items, "usd", PALETTE["yellow"])

    # --- Tokens ---
    tokens_in = sum(r.get("tokens_in") or 0 for r in responses)
    tokens_out = sum(r.get("tokens_out") or 0 for r in responses)
    tok_cfg = panels_cfg["tokens"]
    tok_total = tokens_in + tokens_out
    tok_pass = check_threshold(tok_total, tok_cfg["threshold"])
    tok_chart = bar_chart([("in", tokens_in), ("out", tokens_out)], "tokens", PALETTE["orange"])

    # --- Quality ---
    quality_scores = [r["quality_score"] for r in responses if r.get("quality_score") is not None]
    quality_mean = round(mean(quality_scores), 3) if quality_scores else 0.0
    qual_cfg = panels_cfg["quality"]
    qual_pass = check_threshold(quality_mean, qual_cfg["threshold"])
    qual_chart = bar_chart(
        [("mean", quality_mean)],
        "score",
        PALETTE["blue"],
        threshold_value=qual_cfg["threshold"]["value"],
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<title>{config['title']}</title>
<style>
  body {{ margin:0; background:{PALETTE['page']}; font-family: system-ui,-apple-system,"Segoe UI",sans-serif; }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 24px; }}
  .grid {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-top:16px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style></head>
<body>
<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;">
    <h1 style="margin:0;font-size:20px;color:{PALETTE['ink_primary']};">{config['title']}</h1>
    <div style="font-size:12px;color:{PALETTE['ink_muted']};">
      Time range: {config['time_range_minutes']} phut &middot; Refresh: {config['refresh_seconds']}s &middot; Generated: {generated_at} &middot; Source: data/logs.jsonl ({len(records)} records)
    </div>
  </div>
  <div class="grid">
    {panel_card("Latency percentiles", "ms", f"P95 {p95:g}", lat_pass, lat_chart, f"P50={p50:g}ms P99={p99:g}ms | nguong P95<={lat_cfg['threshold']['value']}ms")}
    {panel_card("Request traffic", "req/min", f"{rate_per_minute}", traf_pass, traf_chart, f"Tong {total_requests} request | nguong >={traf_cfg['threshold']['value']} req/min")}
    {panel_card("Error rate and breakdown", "%", f"{error_rate}", err_pass, err_chart, f"{len(failures)}/{total_requests} that bai | nguong <={err_cfg['threshold']['value']}%")}
    {panel_card("Cost over time", "usd", f"{total_cost}", cost_pass, cost_chart, f"Tong cua so 60 phut | nguong <={cost_cfg['threshold']['value']} usd")}
    {panel_card("Input and output tokens", "tokens", f"{tok_total}", tok_pass, tok_chart, f"in={tokens_in} out={tokens_out} | nguong <={tok_cfg['threshold']['value']}")}
    {panel_card("Quality proxy", "0-1", f"{quality_mean}", qual_pass, qual_chart, f"nguong >={qual_cfg['threshold']['value']}")}
  </div>
</div>
</body></html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")
    print(
        f"latency_p95={p95}ms({'PASS' if lat_pass else 'FAIL'}) "
        f"traffic_rate={rate_per_minute}/min({'PASS' if traf_pass else 'FAIL'}) "
        f"error_rate={error_rate}%({'PASS' if err_pass else 'FAIL'}) "
        f"cost_total={total_cost}usd({'PASS' if cost_pass else 'FAIL'}) "
        f"tokens_total={tok_total}({'PASS' if tok_pass else 'FAIL'}) "
        f"quality_mean={quality_mean}({'PASS' if qual_pass else 'FAIL'})"
    )


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Dung dashboard HTML tu data/logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "dashboard.html")
    args = parser.parse_args()
    build(args.config, args.logs, args.output)


if __name__ == "__main__":
    main()
