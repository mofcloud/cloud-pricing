#!/usr/bin/env python3
"""Build the public CSV/JSON files from MofCloud's hub export.

    python3 scripts/build.py <.hub-export dir> [repo root]

Writes <root>/data/* (committed) and <root>/release/instance-regions.csv.gz
(GitHub Release asset, too big for git). Stdlib only.
"""
import csv, gzip, io, json, os, sys
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

HOURS_PER_MONTH = 730

INSTANCE_COLS = ["provider", "instance_type", "family", "vcpu", "memory_gib", "arch", "cpu_mode",
                 "gpu_model", "gpu_count", "gpu_memory_gib", "regions",
                 "on_demand_usd_hour", "on_demand_usd_month", "on_demand_region", "on_demand_currency",
                 "on_demand_native_hour", "spot_usd_hour", "spot_region",
                 "reserved_usd_hour", "reserved_term", "url"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def num(v):
    """Blank for missing/zero (zero means 'not offered' in the export)."""
    return "" if v in (None, 0, "") else v


def write_csv(path, cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue().encode()
    if str(path).endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    path.write_bytes(data)
    return len(rows)


def region_label(r):
    return r.get("regionNameEn") or r.get("region", "")


def instance_url(provider, itype):
    return f"https://mofcloud.com/tools/servers/{provider}/{quote(itype, safe='')}"


def build(src, root):
    data, rel = root / "data", root / "release"
    data.mkdir(parents=True, exist_ok=True)
    rel.mkdir(parents=True, exist_ok=True)

    catalog = load(src / "catalog.json")
    old = data / "instances.csv"
    if old.exists():  # refuse a broken export (a source failed), like the tools-com CI does
        before = sum(1 for _ in old.open()) - 1
        if len(catalog) < before * 0.75:
            sys.exit(f"instances dropped {before} -> {len(catalog)} (>25%), refusing to overwrite")

    instances, region_rows = [], []
    for c in sorted(catalog, key=lambda r: r["id"]):
        prov, itype = c["provider"], c["instanceType"]
        detail = load(src / "detail" / prov / f"{itype}.json")
        gpu = "" if c.get("gpuModelNorm") == "No Accelerator Card" else c.get("gpuModelNorm", "")
        od = spot = None
        for r in sorted(detail["regions"], key=lambda r: r["region"]):
            p_od = next((p for p in r["prices"] if p["charge"] == "on_demand"), None)
            p_spot = next((p for p in r["prices"] if p["charge"] == "spot"), None)
            if p_od and (od is None or p_od["usd"] < od[1]["usd"]):
                od = (r, p_od)
            if p_spot and p_spot["usd"] > 0 and (spot is None or p_spot["usd"] < spot[1]["usd"]):
                spot = (r, p_spot)
            if p_od or p_spot:
                region_rows.append({
                    "provider": prov, "instance_type": itype, "vcpu": c["vcpu"], "memory_gib": c["memGib"],
                    "cpu_mode": c["cpuMode"], "gpu_model": gpu, "gpu_count": c.get("gpuCount", ""),
                    "region": r["region"], "region_name": region_label(r), "country": r.get("country", ""),
                    "currency": (p_od or p_spot)["currency"],
                    "on_demand_native_hour": p_od["native"] if p_od else "",
                    "on_demand_usd_hour": p_od["usd"] if p_od else "",
                    "spot_usd_hour": num(p_spot and p_spot["usd"]),
                })
        terms = c.get("terms") or {}
        rsv_term = next((k for k, t in terms.items() if k != "1m" and t.get("usd") == c.get("minRsvUsd")), "")
        instances.append({
            "provider": prov, "instance_type": itype, "family": c["family"], "vcpu": c["vcpu"],
            "memory_gib": c["memGib"], "arch": c["arch"], "cpu_mode": c["cpuMode"],
            "gpu_model": gpu, "gpu_count": c.get("gpuCount", ""),
            "gpu_memory_gib": c.get("gpuMemGib", ""), "regions": c["regions"],
            "on_demand_usd_hour": od[1]["usd"] if od else "",
            "on_demand_usd_month": round(od[1]["usd"] * HOURS_PER_MONTH, 2) if od else "",
            "on_demand_region": od[0]["region"] if od else "",
            "on_demand_currency": od[1]["currency"] if od else "",
            "on_demand_native_hour": od[1]["native"] if od else "",
            "spot_usd_hour": spot[1]["usd"] if spot else "", "spot_region": spot[0]["region"] if spot else "",
            "reserved_usd_hour": num(c.get("minRsvUsd")) if rsv_term else "", "reserved_term": rsv_term,
            "url": instance_url(prov, itype),
        })

    counts = {}
    counts["instances.csv"] = write_csv(data / "instances.csv", INSTANCE_COLS, instances)
    counts["gpu-instances.csv"] = write_csv(data / "gpu-instances.csv", INSTANCE_COLS,
                                            [r for r in instances if r["gpu_model"]])
    counts["instance-regions.csv.gz"] = write_csv(rel / "instance-regions.csv.gz", list(region_rows[0]), region_rows)

    disks = []
    for s in sorted(load(src / "storage-catalog.json"), key=lambda r: r["id"]):
        d = load(src / "storage-detail" / s["provider"] / f"{s['diskType']}.json")
        for r in sorted(d["regionsList"], key=lambda r: r["region"]):
            disks.append({"provider": s["provider"], "disk_type": s["diskType"], "category": s["category"],
                          "media": s["media"], "pricing_model": s["perfModel"], "region": r["region"],
                          "region_name": region_label(r), "country": r.get("country", ""),
                          "usd_per_gib_month": r["usdGibMo"], "currency": r["currency"],
                          "native_per_gib_month": r["native"], "max_iops": s.get("maxIops", ""),
                          "max_throughput_mbps": s.get("maxTputMbps", "")})
    counts["disks.csv"] = write_csv(data / "disks.csv", list(disks[0]), disks)

    net = load(src / "network-catalog.json")
    key = lambda r: (r["provider"], r["region"], r.get("chargeType", ""), r.get("scope", ""))
    common = ["provider", "region", "region_name", "country"]
    def base(r):
        return {"provider": r["provider"], "region": r["region"], "region_name": region_label(r), "country": r.get("country", "")}
    counts["egress.csv"] = write_csv(data / "egress.csv",
        common + ["first_gb_usd", "avg_usd_per_gb_at_1tib", "usd_per_1tib_month", "destination_based"],
        [{**base(r), "first_gb_usd": r["firstGbUsd"], "avg_usd_per_gb_at_1tib": r["perGbUsd"],
          "usd_per_1tib_month": r["monthlyUsd"], "destination_based": "yes" if r.get("destBased") else ""}
         for r in sorted(net["egress"], key=key)])
    counts["bandwidth.csv"] = write_csv(data / "bandwidth.csv",
        common + ["charge_type", "first_mbps_usd_month", "avg_usd_per_mbps_at_100mbps", "usd_per_100mbps_month"],
        [{**base(r), "charge_type": r["chargeType"], "first_mbps_usd_month": r["firstMbpsUsd"],
          "avg_usd_per_mbps_at_100mbps": r["perMbpsUsd"], "usd_per_100mbps_month": r["monthlyUsd"]}
         for r in sorted(net["bandwidth"], key=key)])
    counts["public-ip.csv"] = write_csv(data / "public-ip.csv", common + ["scope", "usd_hour", "usd_month"],
        [{**base(r), "scope": r["scope"], "usd_hour": r["hourlyUsd"], "usd_month": r["monthlyUsd"]}
         for r in sorted(net["eip"], key=key)])

    changes = src / "changes.json"
    if changes.exists():
        (data / "changes.json").write_bytes(changes.read_bytes())

    synced = net.get("generatedAt") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {"synced_at": synced, "rows": counts, "providers": sorted({r["provider"] for r in instances}),
            "source": "https://mofcloud.com/tools", "license": "CC-BY-4.0"}
    (data / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for k, v in counts.items():
        print(f"{k}: {v} rows")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
