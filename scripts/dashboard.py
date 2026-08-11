#!/usr/bin/env python3
import json
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
PORT = 8501

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Day 13 AI Observability Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-purple: #c084fc;
            --accent-amber: #fbbf24;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }
        h1 { margin: 0; font-size: 24px; color: var(--accent-blue); }
        .meta { color: var(--text-sub); font-size: 14px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .card-title { font-size: 16px; font-weight: 600; color: var(--text-main); }
        .badge {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .chart-container { position: relative; height: 240px; width: 100%; }
        .stats-row {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }
        .stat-box {
            flex: 1;
            background: rgba(15, 23, 42, 0.5);
            padding: 10px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .stat-label { font-size: 11px; color: var(--text-sub); text-transform: uppercase; }
        .stat-value { font-size: 18px; font-weight: 700; margin-top: 4px; }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Day 13 AI Observability Dashboard</h1>
            <div class="meta">Nguồn: data/logs.jsonl | Refresh 30s | Quản lý SLO & Metrics API</div>
        </div>
        <button onclick="location.reload()" style="background: var(--accent-blue); color: #000; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">Tải lại dữ liệu</button>
    </header>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency Percentiles (ms)</span>
                <span class="badge">Threshold P95 &le; 3000ms</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">P50 Latency</div><div class="stat-value" id="p50-val">-</div></div>
                <div class="stat-box"><div class="stat-label">P95 Latency</div><div class="stat-value" id="p95-val" style="color: var(--accent-green);">-</div></div>
                <div class="stat-box"><div class="stat-label">P99 Latency</div><div class="stat-value" id="p99-val">-</div></div>
            </div>
            <div class="chart-container"><canvas id="latencyChart"></canvas></div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request Traffic (req/min)</span>
                <span class="badge">Threshold &ge; 1 req/min</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Tổng Requests</div><div class="stat-value" id="total-reqs">-</div></div>
                <div class="stat-box"><div class="stat-label">Tốc độ trung bình</div><div class="stat-value" id="rate-reqs">-</div></div>
            </div>
            <div class="chart-container"><canvas id="trafficChart"></canvas></div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error Rate & Breakdown (%)</span>
                <span class="badge">Threshold &le; 2%</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Error Rate</div><div class="stat-value" id="error-rate" style="color: var(--accent-green);">0%</div></div>
                <div class="stat-box"><div class="stat-label">Tổng số lỗi</div><div class="stat-value" id="error-count">0</div></div>
            </div>
            <div class="chart-container"><canvas id="errorChart"></canvas></div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost over Time (USD)</span>
                <span class="badge">Threshold &le; $2.50</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Tổng Chi Phí</div><div class="stat-value" id="total-cost" style="color: var(--accent-amber);">$0.00</div></div>
                <div class="stat-box"><div class="stat-label">Chi phí / Request</div><div class="stat-value" id="avg-cost">$0.00</div></div>
            </div>
            <div class="chart-container"><canvas id="costChart"></canvas></div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Input & Output Tokens</span>
                <span class="badge">Threshold &le; 50,000</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Tokens In</div><div class="stat-value" id="tokens-in">-</div></div>
                <div class="stat-box"><div class="stat-label">Tokens Out</div><div class="stat-value" id="tokens-out">-</div></div>
                <div class="stat-box"><div class="stat-label">Tổng Tokens</div><div class="stat-value" id="tokens-total" style="color: var(--accent-purple);">-</div></div>
            </div>
            <div class="chart-container"><canvas id="tokenChart"></canvas></div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality Proxy Score</span>
                <span class="badge">Threshold &ge; 0.75</span>
            </div>
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Mean Quality Score</div><div class="stat-value" id="quality-score" style="color: var(--accent-green);">-</div></div>
            </div>
            <div class="chart-container"><canvas id="qualityChart"></canvas></div>
        </div>
    </div>

    <script>
        async function loadData() {
            const res = await fetch('/api/metrics');
            const data = await res.json();

            // 1. Latency
            document.getElementById('p50-val').innerText = data.latency.p50 + ' ms';
            document.getElementById('p95-val').innerText = data.latency.p95 + ' ms';
            document.getElementById('p99-val').innerText = data.latency.p99 + ' ms';
            
            new Chart(document.getElementById('latencyChart'), {
                type: 'bar',
                data: {
                    labels: data.latency.items.map((_, i) => '#' + (i + 1)),
                    datasets: [
                        { label: 'Latency (ms)', data: data.latency.items, backgroundColor: '#38bdf8' },
                        { label: 'Threshold (3000ms)', data: data.latency.items.map(() => 3000), borderColor: '#f87171', type: 'line', borderDash: [5, 5], pointRadius: 0 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });

            // 2. Traffic
            document.getElementById('total-reqs').innerText = data.traffic.total;
            document.getElementById('rate-reqs').innerText = data.traffic.rate + ' req/min';
            new Chart(document.getElementById('trafficChart'), {
                type: 'line',
                data: {
                    labels: data.traffic.timestamps,
                    datasets: [{ label: 'Requests', data: data.traffic.counts, borderColor: '#4ade80', backgroundColor: 'rgba(74, 222, 128, 0.1)', fill: true }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });

            // 3. Errors
            document.getElementById('error-rate').innerText = data.errors.rate + '%';
            document.getElementById('error-count').innerText = data.errors.failed;
            new Chart(document.getElementById('errorChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data.errors.breakdown).length ? Object.keys(data.errors.breakdown) : ['Success', 'Failed'],
                    datasets: [{ data: Object.keys(data.errors.breakdown).length ? Object.values(data.errors.breakdown) : [data.traffic.total - data.errors.failed, data.errors.failed], backgroundColor: ['#4ade80', '#f87171'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });

            // 4. Cost
            document.getElementById('total-cost').innerText = '$' + data.cost.total.toFixed(4);
            document.getElementById('avg-cost').innerText = '$' + (data.cost.total / (data.traffic.total || 1)).toFixed(4);
            new Chart(document.getElementById('costChart'), {
                type: 'line',
                data: {
                    labels: data.cost.timestamps,
                    datasets: [{ label: 'Cumulative Cost ($)', data: data.cost.cumulative, borderColor: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.1)', fill: true }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });

            // 5. Tokens
            document.getElementById('tokens-in').innerText = data.tokens.in.toLocaleString();
            document.getElementById('tokens-out').innerText = data.tokens.out.toLocaleString();
            document.getElementById('tokens-total').innerText = (data.tokens.in + data.tokens.out).toLocaleString();
            new Chart(document.getElementById('tokenChart'), {
                type: 'bar',
                data: {
                    labels: ['Input Tokens', 'Output Tokens'],
                    datasets: [{ label: 'Tokens', data: [data.tokens.in, data.tokens.out], backgroundColor: ['#c084fc', '#38bdf8'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });

            // 6. Quality
            document.getElementById('quality-score').innerText = data.quality.mean.toFixed(2);
            new Chart(document.getElementById('qualityChart'), {
                type: 'line',
                data: {
                    labels: data.quality.scores.map((_, i) => '#' + (i + 1)),
                    datasets: [
                        { label: 'Quality Score', data: data.quality.scores, borderColor: '#4ade80', backgroundColor: 'rgba(74, 222, 128, 0.2)' },
                        { label: 'Threshold (0.75)', data: data.quality.scores.map(() => 0.75), borderColor: '#f87171', type: 'line', borderDash: [5, 5], pointRadius: 0 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 1 } }, plugins: { legend: { labels: { color: '#94a3b8' } } } }
            });
        }
        loadData();
    </script>
</body>
</html>
"""

def parse_logs() -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {
            "latency": {"p50": 0, "p95": 0, "p99": 0, "items": []},
            "traffic": {"total": 0, "rate": 0, "timestamps": [], "counts": []},
            "errors": {"rate": 0, "failed": 0, "breakdown": {}},
            "cost": {"total": 0, "timestamps": [], "cumulative": []},
            "tokens": {"in": 0, "out": 0},
            "quality": {"mean": 0, "scores": []},
        }

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    received = [r for r in records if r.get("event") == "request_received"]
    sent = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = sorted([r.get("latency_ms", 0) for r in sent if "latency_ms" in r])
    def pct(arr: list[int], p: float) -> int:
        if not arr:
            return 0
        idx = int(len(arr) * p)
        return arr[min(idx, len(arr) - 1)]

    p50 = pct(latencies, 0.50)
    p95 = pct(latencies, 0.95)
    p99 = pct(latencies, 0.99)

    costs = [r.get("cost_usd", 0.0) for r in sent]
    cum_cost = []
    curr = 0.0
    for c in costs:
        curr += c
        cum_cost.append(round(curr, 6))

    tokens_in = sum(r.get("tokens_in", 0) for r in sent)
    tokens_out = sum(r.get("tokens_out", 0) for r in sent)
    qualities = [r.get("quality_score", 0.0) for r in sent]
    mean_q = sum(qualities) / len(qualities) if qualities else 0.0

    error_breakdown: dict[str, int] = {}
    for f in failed:
        et = f.get("error_type", "UnknownError")
        error_breakdown[et] = error_breakdown.get(et, 0) + 1

    err_rate = round((len(failed) / len(received) * 100), 2) if received else 0.0

    return {
        "latency": {"p50": p50, "p95": p95, "p99": p99, "items": latencies},
        "traffic": {
            "total": len(received),
            "rate": len(received),
            "timestamps": [r.get("ts", "")[11:19] for r in received],
            "counts": list(range(1, len(received) + 1)),
        },
        "errors": {
            "rate": err_rate,
            "failed": len(failed),
            "breakdown": error_breakdown,
        },
        "cost": {
            "total": round(curr, 6),
            "timestamps": [r.get("ts", "")[11:19] for r in sent],
            "cumulative": cum_cost,
        },
        "tokens": {"in": tokens_in, "out": tokens_out},
        "quality": {"mean": round(mean_q, 2), "scores": qualities},
    }


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = parse_logs()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_error(404)

def main() -> None:
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), DashboardHandler) as httpd:
        print(f"--- Day 13 Observability Dashboard ---")
        print(f"Dashboard running at: http://127.0.0.1:{PORT}")
        print(f"Nguồn dữ liệu: {LOG_PATH}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")

if __name__ == "__main__":
    main()
