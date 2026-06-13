import { Request } from "express";
import { getRequestHostname } from "../host-utils";

function mockReq(headers: Record<string, string> = {}): Request {
  const lower: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    lower[k.toLowerCase()] = v;
  }
  return {
    get: (name: string) => lower[name.toLowerCase()],
  } as unknown as Request;
}

describe("getRequestHostname", () => {
  const original = process.env.SELF_HOSTED_DOMAIN;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.SELF_HOSTED_DOMAIN;
    } else {
      process.env.SELF_HOSTED_DOMAIN = original;
    }
  });

  it("falls back to the request host when nothing is configured", () => {
    delete process.env.SELF_HOSTED_DOMAIN;
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("localhost:3002");
  });

  it("prefers SELF_HOSTED_DOMAIN over the request host", () => {
    process.env.SELF_HOSTED_DOMAIN = "api.example.com";
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("api.example.com");
  });

  it("keeps an explicit port in SELF_HOSTED_DOMAIN", () => {
    process.env.SELF_HOSTED_DOMAIN = "api.example.com:8080";
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("api.example.com:8080");
  });

  it("strips a scheme and path from SELF_HOSTED_DOMAIN", () => {
    process.env.SELF_HOSTED_DOMAIN = "https://api.example.com/firecrawl";
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("api.example.com");
  });

  it("ignores an empty or whitespace SELF_HOSTED_DOMAIN", () => {
    process.env.SELF_HOSTED_DOMAIN = "   ";
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("localhost:3002");
  });

  it("falls through to the request host when SELF_HOSTED_DOMAIN is unparseable", () => {
    process.env.SELF_HOSTED_DOMAIN = "not a valid host";
    const req = mockReq({ host: "localhost:3002" });
    expect(getRequestHostname(req)).toBe("localhost:3002");
  });

  it("uses the first X-Forwarded-Host when no domain is configured", () => {
    delete process.env.SELF_HOSTED_DOMAIN;
    const req = mockReq({
      "x-forwarded-host": "public.example.com, internal.local",
      host: "localhost:3002",
    });
    expect(getRequestHostname(req)).toBe("public.example.com");
  });

  it("prefers SELF_HOSTED_DOMAIN over X-Forwarded-Host", () => {
    process.env.SELF_HOSTED_DOMAIN = "api.example.com";
    const req = mockReq({
      "x-forwarded-host": "public.example.com",
      host: "localhost:3002",
    });
    expect(getRequestHostname(req)).toBe("api.example.com");
  });
});
