# DNS Query Encoding in DNS-over-HTTPS (DoH)

## Why DNS Queries Must Be Encoded

When using DNS-over-HTTPS with GET requests, DNS queries must be encoded using base64url encoding. This requirement exists for several important technical reasons:

### 1. Binary Data in URLs

DNS queries are binary data structures that contain information about the domain name being queried, the type of record requested (A, AAAA, MX, etc.), and other metadata. URLs, however, are text-based and have restrictions on what characters they can contain.

### 2. URL Safety

Standard Base64 encoding uses characters like '+' and '/' which have special meanings in URLs:
- '+' is interpreted as a space in URL query parameters
- '/' is interpreted as a path separator

Base64url encoding solves this by:
- Replacing '+' with '-'
- Replacing '/' with '_'
- Optionally omitting padding '=' characters

### 3. RFC 8484 Compliance

The DNS-over-HTTPS specification (RFC 8484) mandates the use of base64url encoding for DNS queries transmitted via GET requests to ensure interoperability between different DoH implementations.

## Example Encoding Process

1. A DNS query for "example.com" is represented as binary data
2. This binary data is encoded using base64url encoding
3. The resulting string is safe to use in a URL query parameter

For example:
```
Binary DNS Query → Base64url Encoding → URL Parameter
[0x12, 0x34, ...] → "q80BAAAB..." → ?dns=q80BAAAB...
```

## When Encoding is Required

- **GET Requests**: DNS queries MUST be base64url-encoded
- **POST Requests**: DNS queries are sent as binary data in the request body (no encoding needed)

### Using POST Requests to Avoid Encoding

If you prefer to avoid base64url encoding entirely, you can use POST requests to send raw binary DNS queries. This method:

1. Eliminates the need for any encoding transformations
2. Sends the DNS query directly as binary data in the request body
3. Still complies with RFC 8484 for DNS-over-HTTPS
4. Requires setting the `Content-Type: application/dns-message` header

Example with curl:
```bash
curl -H "Content-Type: application/dns-message" \
     --data-binary @query.dns \
     https://your-doh-endpoint/dns-query
```

This approach is particularly useful when:
- Working with clients that don't have base64 encoding capabilities
- You want to reduce processing overhead
- You prefer to work with raw binary data

## Tools for Encoding

Many programming languages provide built-in functions for base64url encoding:
- JavaScript: `base64url.encode()`
- Python: `base64.urlsafe_b64encode()`
- Command-line: `openssl base64 -url`

This encoding requirement ensures that DNS queries can be safely transmitted over HTTPS while maintaining compatibility with web standards and the DoH protocol specification.