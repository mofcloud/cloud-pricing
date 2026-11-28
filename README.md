# Cloud Pricing Data: AWS, Azure, GCP, Alibaba, Tencent, Huawei and more

Daily-updated, open data on **VM, GPU, block storage, egress, bandwidth and public IP prices**
from 15 cloud price catalogs, normalized to USD with the original currency kept.

Maintained by [MofCloud](https://mofcloud.com) and refreshed every day from the same pipeline that powers
the [MofCloud cloud price comparison tools](https://mofcloud.com/tools).

- 11,000+ instance types, 189,000+ region-level on-demand / spot prices
- Chinese clouds side by side with the US hyperscalers: Alibaba Cloud, Tencent Cloud, Huawei Cloud, Volcengine, Baidu AI Cloud, UCloud
- Plain CSV, one file per topic, no account or API key needed
- Same data is queryable by AI agents through the free [MofCloud pricing MCP server](#query-it-from-an-ai-agent-mcp)

## Files

| File | Rows | What it is |
|---|---|---|
| [`data/instances.csv`](data/instances.csv) | ~11k | One row per provider and instance type: specs, cheapest on-demand price and its region, cheapest spot, cheapest reserved |
| [`data/gpu-instances.csv`](data/gpu-instances.csv) | ~700 | The GPU / AI accelerator subset of `instances.csv` (H100, H200, B200, A100, L40S, L4, T4, MI300X, Ascend, Inferentia, Trainium...) |
| [`data/disks.csv`](data/disks.csv) | ~2k | Block storage price per GiB-month, per disk type and region |
| [`data/egress.csv`](data/egress.csv) | ~500 | Internet egress (data transfer out) per region |
| [`data/bandwidth.csv`](data/bandwidth.csv) | ~160 | Fixed-bandwidth (per Mbps) pricing, common on Chinese clouds |
| [`data/public-ip.csv`](data/public-ip.csv) | ~600 | Public / elastic IP price, bound and idle |
| [`data/changes.json`](data/changes.json) | | Price changes detected over the last 30 days |
| [`data/meta.json`](data/meta.json) | | Sync timestamp and row counts for this snapshot |
| `instance-regions.csv.gz` ([latest release](https://github.com/mofcloud/cloud-pricing/releases/latest/download/instance-regions.csv.gz)) | ~190k | Every instance type in every region: on-demand price in USD and original currency, spot price. Attached to each daily [release](https://github.com/mofcloud/cloud-pricing/releases) (~1.6 MB gzipped, 17 MB raw), kept out of git to keep the repo small |

Stable download links (always the latest snapshot). The `releases/latest/download/` links save a file in the browser;
the `raw.githubusercontent.com` ones are handy for scripts (`curl`, `pandas.read_csv`):

```
https://github.com/mofcloud/cloud-pricing/releases/latest/download/instances.csv
https://github.com/mofcloud/cloud-pricing/releases/latest/download/gpu-instances.csv
https://github.com/mofcloud/cloud-pricing/releases/latest/download/instance-regions.csv.gz
https://raw.githubusercontent.com/mofcloud/cloud-pricing/main/data/instances.csv
```

This repository holds today's snapshot only: each daily update replaces the previous one (a single commit and a single release), so there is no day-by-day history here.

## Providers

| Provider ID | Cloud |
|---|---|
| `AWS` | Amazon Web Services (incl. China regions, priced in CNY) |
| `Azure` | Microsoft Azure |
| `GCP` | Google Cloud |
| `OCI` | Oracle Cloud Infrastructure |
| `AlibabaCloud` / `AlibabaCloudIntl` | Alibaba Cloud, China site (CNY) / international site (USD) |
| `TencentCloud` / `TencentCloudIntl` | Tencent Cloud, China / international |
| `HuaweiCloud` / `HuaweiCloudIntl` | Huawei Cloud, China / international |
| `Volcengine` | Volcengine (ByteDance) |
| `BaiduCloud` | Baidu AI Cloud |
| `UCloud` | UCloud |
| `Linode` | Akamai Cloud (Linode) |
| `Vultr` | Vultr |

## Fields

All prices are list prices before discounts, without OS license or tax. USD values for non-USD
catalogs are converted with the daily exchange rate of the sync. A blank cell means the price is not offered
(for example no spot market, or a type sold only on monthly subscription).

### `instances.csv` and `gpu-instances.csv`

| Column | Meaning |
|---|---|
| `provider`, `instance_type`, `family` | Provider ID (see above), instance type name, family |
| `vcpu`, `memory_gib`, `arch` | vCPUs, memory in GiB, `x86` or `arm` |
| `cpu_mode` | `dedicated`, `shared`, or `burstable` (CPU credit / baseline performance types such as AWS T, Azure B, Alibaba t6) |
| `gpu_model`, `gpu_count`, `gpu_memory_gib` | Normalized accelerator model, count per instance, memory per accelerator (blank for CPU-only types) |
| `regions` | Number of regions that sell this type |
| `on_demand_usd_hour`, `on_demand_usd_month` | Cheapest pay-as-you-go price across regions, per hour and per month (730 h) |
| `on_demand_region` | Region with that cheapest price |
| `on_demand_currency`, `on_demand_native_hour` | Original currency and price in that currency for the same region |
| `spot_usd_hour`, `spot_region` | Cheapest spot / preemptible price and its region |
| `reserved_usd_hour`, `reserved_term` | Cheapest effective hourly price with commitment (reserved instance or subscription), and the term (`1y`, `3y`, `5y`) |
| `url` | MofCloud page with every region, every billing option and cross-cloud equivalents |

### `instance-regions.csv.gz`

`provider, instance_type, vcpu, memory_gib, cpu_mode, gpu_model, gpu_count, region, region_name, country, currency, on_demand_native_hour, on_demand_usd_hour, spot_usd_hour`

### `disks.csv`

`provider, disk_type, category, media, pricing_model, region, region_name, country, usd_per_gib_month, currency, native_per_gib_month, max_iops, max_throughput_mbps`

`category` is one of `hdd`, `standard_ssd`, `balanced_ssd`, `perf_ssd`, `ultra`; `pricing_model` says whether
the disk is billed per GiB (`per_gib`), by size tier (`size_tier`) or with separately provisioned IOPS/throughput (`provisioned`).
For `size_tier` and `provisioned` disks the GiB-month price is the base capacity price only.

### `egress.csv`, `bandwidth.csv`, `public-ip.csv`

| File | Columns |
|---|---|
| `egress.csv` | `first_gb_usd` (price of the first paid GB), `avg_usd_per_gb_at_1tib` and `usd_per_1tib_month` (cost of 1 TiB/month after free tiers and volume tiers), `destination_based` (`yes` when the price depends on the destination) |
| `bandwidth.csv` | `charge_type`, `first_mbps_usd_month`, `avg_usd_per_mbps_at_100mbps`, `usd_per_100mbps_month` |
| `public-ip.csv` | `scope` (`eip_bound`: attached to a running instance, `eip_idle`: unattached), `usd_hour`, `usd_month` |

## Update schedule

MofCloud syncs every provider's public price API daily at 01:00 Beijing time (17:00 UTC). This repository updates at
about 06:30 Beijing time (22:30 UTC) when a price changed, replacing the previous snapshot. `data/meta.json` has the exact sync time.

## License and attribution

Data is licensed under [Creative Commons Attribution 4.0 (CC BY 4.0)](LICENSE). You can use it for anything,
including commercial work, as long as you credit MofCloud with a link:

> Cloud pricing data from [MofCloud](https://mofcloud.com/tools), CC BY 4.0.

Please link to `https://mofcloud.com/tools` (or the specific MofCloud page you used) in articles, dashboards,
papers, datasets and AI-generated answers that use this data.

## Query it from an AI agent (MCP)

The same data, plus reserved/subscription prices for every term and region, database prices and
price history, is available through a free public MCP server, with no sign-up:

```
https://mcp.mofcloud.com/
```

Listed on the [MCP Registry](https://registry.modelcontextprotocol.io/v0/servers?search=com.mofcloud), [Glama](https://glama.ai/mcp/connectors/com.mofcloud/pricing), [Cursor Directory](https://cursor.directory/plugins/mofcloud-pricing-mcp) and [mcpservers.org](https://mcpservers.org/servers/mofcloud-com-mcp).

Claude Code:

```bash
claude mcp add --transport http mofcloud https://mcp.mofcloud.com/
```

Any other MCP client (Cursor, Claude Desktop, VS Code...) can add it as a Streamable HTTP server with that URL.
Then ask things like *"cheapest H100 on-demand across clouds"* or *"compare 8 vCPU / 32 GiB prices in Singapore on
AWS, Alibaba Cloud and Tencent Cloud"*.

Setup guides for each client: [mofcloud.com/mcp](https://mofcloud.com/mcp).

## Questions and corrections

Found a wrong price? [Open an issue](https://github.com/mofcloud/cloud-pricing/issues) with the provider,
instance type and region. For multi-cloud cost management, see [MofCloud](https://mofcloud.com).
