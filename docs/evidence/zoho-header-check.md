# Zoho outbound header check

Authentication check of a real message sent from Zoho Mail on
`csetioko.me` to a Gmail inbox, read from Gmail's "Show original" headers.

- **Message:** "Test:02 real outbound", sent 2026-10-13 15:10:53 PDT
- **From:** `chris@csetioko.me` (Zoho Mail)
- **To:** a Gmail address
- **Message-Id:** `<1a137518c3b.c262705186462.5682678623192881766@csetioko.me>`
- **Sending server:** `sender6-of-o52.zoho.com` (`165.173.180.52`), TLS 1.3

## Result

SPF, DKIM and DMARC all passed, and all three passed for `csetioko.me`.

| Check | Result | Domain checked | Evidence |
| ----- | ------ | -------------- | -------- |
| SPF   | pass   | `csetioko.me` (envelope sender `chris@csetioko.me`) | `165.173.180.52` is permitted by `v=spf1 include:zohomail.com ~all` |
| DKIM  | pass   | `csetioko.me`, selector `zmail` | `DKIM-Signature: d=csetioko.me; s=zmail`; Gmail reports `dkim=pass header.i=@csetioko.me header.s=zmail` |
| DMARC | pass   | `csetioko.me` (header From) | `dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=csetioko.me` |

The verdicts come from Gmail's own `Authentication-Results` header, added
on receipt.

## What it shows

- **Alignment:** the From domain is `csetioko.me`, and both SPF and DKIM
  passed for that same domain rather than a Zoho domain. DMARC needs only
  one aligned pass; both are aligned.
- **DKIM key:** the pass confirms that the `zmail._domainkey.csetioko.me`
  key published in Cloudflare matches the key Zoho signs with, which a DNS
  lookup alone could not prove (see [dns-before-zoho.md](dns-before-zoho.md)).
- **ARC:** Zoho (`d=zohomail.com`, `i=1`) recorded the same three passes,
  and Gmail sealed them (`i=2`, `cv=pass`). ARC does not change the result.
- **Policy:** `p=NONE` means DMARC failures would only be reported, not
  blocked. Gmail took no action (`dis=NONE`). With outbound mail passing,
  the policy can be tightened to `p=quarantine`, then `p=reject`.

## Relevant headers

Message body and MIME parts omitted; signature hashes shortened with `…`.

```
Authentication-Results: mx.google.com;
       dkim=pass header.i=@csetioko.me header.s=zmail header.b="G5u/Sa16";
       arc=pass (i=1 spf=pass spfdomain=csetioko.me dkim=pass dkdomain=csetioko.me dmarc=pass fromdomain=csetioko.me>);
       spf=pass (google.com: domain of chris@csetioko.me designates 165.173.180.52 as permitted sender) smtp.mailfrom=chris@csetioko.me;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=csetioko.me
Received-SPF: pass (google.com: domain of chris@csetioko.me designates 165.173.180.52 as permitted sender) client-ip=165.173.180.52;
Return-Path: <chris@csetioko.me>
Received: from sender6-of-o52.zoho.com (sender6-of-o52.zoho.com. [165.173.180.52])
       by mx.google.com with ESMTPS ... (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);
       Tue, 13 Oct 2026 15:10:57 -0700 (PDT)
ARC-Seal: i=2; a=rsa-sha256; t=1791929457; cv=pass; d=google.com; s=arc-20260327; b=…
ARC-Seal: i=1; a=rsa-sha256; t=1791929456; cv=none; d=zohomail.com; s=zohoarc; b=…
ARC-Authentication-Results: i=1; mx.zohomail.com; dkim=pass header.i=csetioko.me;
       spf=pass smtp.mailfrom=chris@csetioko.me; dmarc=pass header.from=<chris@csetioko.me>
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/relaxed; t=1791929456; s=zmail;
       d=csetioko.me; i=chris@csetioko.me;
       h=Date:Date:From:From:To:To:Message-Id:Message-Id:Subject:Subject:MIME-Version:Content-Type:Reply-To:Cc;
       bh=r3/RWJo8XYGgMrZA2KIfRV6YJsdg3OmzMcoubxWMz78=; b=G5u/Sa16…
Received: from mail.zoho.com by mx.zohomail.com with SMTP id 1791929453642265.736375757842;
       Tue, 13 Oct 2026 15:10:53 -0700 (PDT)
Date: Tue, 13 Oct 2026 15:10:53 -0700
From: Chris Setioko <chris@csetioko.me>
Message-Id: <1a137518c3b.c262705186462.5682678623192881766@csetioko.me>
Subject: Test:02 real outbound
User-Agent: Zoho Mail
X-Mailer: Zoho Mail
```
