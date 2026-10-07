# How This Site Is Secured

## How do I know my data to your site is encrypted?

 Data is encrypted because the browser and my server communicate over HTTPS, which means all communication is encrypted  using TLS. 

## Certificate Details and How Renewal Works

My TLS certificate was issued by **Let's Encrypt**. It covers: both `owsetioko.me` and `www.owsetioko.me`. And It expires on January 7 2026 because it expires every 90 days. Certbot handles renewal automatically twice a day. I can verify this by running: 

sudo certbot renew --dry-run

And 

systemctl list-timers | grep certbot

## Open Ports

Port 22 is restricted to my specific IP address in the Azure Network 
Port 443 is the https network and it serves the website securely to anyone 
Port 80 redirects the https to anyone. 

## Where Encryption Starts and Ends

Encryption starts at the visitor's browser and ends at Nginx on my VM. 

## How to Check the Certificate in Chrome

You can check by clicking the icon next to the url and checking the connection is secure or not. Also the certificate information is there. 

## OpenSSL Verification

```
$ openssl s_client -connect csetioko.me:443 -servername csetioko.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
subject= /CN=csetioko.me
issuer= /C=US/O=Let's Encrypt/CN=YE2
notBefore=Oct  7 10:04:33 2026 GMT
notAfter=Jan  5 10:04:32 2027 GMT
```
