# DNS before Zoho Mail

Snapshot of every DNS record for `csetioko.me`, taken before adding any
Zoho Mail records, so the change can be compared or rolled back.

- **Captured:** 2026-10-13 21:13:55 UTC
- **Source:** Cloudflare CLI (`cf` 1.0.0-beta.16), zone `csetioko.me`
- **Nameservers:** `christina.ns.cloudflare.com`, `jermaine.ns.cloudflare.com`
- **Record count:** 3 (plus Cloudflare-managed SOA and NS)

## Records

| Type  | Name                          | Content                                                                              | TTL  | Proxied |
| ----- | ----------------------------- | ------------------------------------------------------------------------------------ | ---- | ------- |
| A     | `www.csetioko.me`             | `20.88.61.1`                                                                         | Auto | No      |
| CNAME | `csetioko.me`                 | `tbtcq5cj.up.railway.app`                                                            | Auto | No      |
| TXT   | `_railway-verify.csetioko.me` | `"railway-verify=3f52596765fc6384ada67aa8c36717a7d8ddca197ccd29dabf512cdb8b370e13"` | Auto | No      |

TTL `1` in Cloudflare means "Auto".

There are no MX, SPF, DKIM or DMARC records yet, so the domain does not
receive or authenticate email at this point.

## Raw export

```
cf dns records export --zone csetioko.me
```

```
;; Domain:     csetioko.me.
;; Exported:   2026-10-13 21:13:55

;; SOA Record
csetioko.me	3600	IN	SOA	christina.ns.cloudflare.com. dns.cloudflare.com. 2054359263 10000 2400 604800 3600

;; NS Records
csetioko.me.	86400	IN	NS	christina.ns.cloudflare.com.
csetioko.me.	86400	IN	NS	jermaine.ns.cloudflare.com.

;; A Records
www.csetioko.me.	1	IN	A	20.88.61.1 ; cf_tags=cf-proxied:false

;; CNAME Records
csetioko.me.	1	IN	CNAME	tbtcq5cj.up.railway.app. ; cf_tags=cf-proxied:false

;; TXT Records
_railway-verify.csetioko.me.	1	IN	TXT	"railway-verify=3f52596765fc6384ada67aa8c36717a7d8ddca197ccd29dabf512cdb8b370e13"
```

The export's boilerplate header comment (BIND usage disclaimer) is omitted.
