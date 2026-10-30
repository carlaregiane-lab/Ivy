import assert from "node:assert/strict";
import test from "node:test";
import { hasGatewayAuthentication } from "../lib/ai/gateway-auth.ts";

test("recognizes deployed request OIDC as well as local credentials", (t) => {
  const contextSymbol = Symbol.for("@vercel/request-context");
  const originalContext = Object.getOwnPropertyDescriptor(globalThis, contextSymbol);
  const originalKey = process.env.AI_GATEWAY_API_KEY;
  const originalToken = process.env.VERCEL_OIDC_TOKEN;

  t.after(() => {
    if (originalContext) Object.defineProperty(globalThis, contextSymbol, originalContext);
    else Reflect.deleteProperty(globalThis, contextSymbol);
    if (originalKey === undefined) delete process.env.AI_GATEWAY_API_KEY;
    else process.env.AI_GATEWAY_API_KEY = originalKey;
    if (originalToken === undefined) delete process.env.VERCEL_OIDC_TOKEN;
    else process.env.VERCEL_OIDC_TOKEN = originalToken;
  });

  delete process.env.AI_GATEWAY_API_KEY;
  delete process.env.VERCEL_OIDC_TOKEN;
  Reflect.deleteProperty(globalThis, contextSymbol);
  assert.equal(hasGatewayAuthentication(), false);

  process.env.AI_GATEWAY_API_KEY = "test-local-key";
  assert.equal(hasGatewayAuthentication(), true);
  delete process.env.AI_GATEWAY_API_KEY;

  process.env.VERCEL_OIDC_TOKEN = "test-local-oidc";
  assert.equal(hasGatewayAuthentication(), true);
  delete process.env.VERCEL_OIDC_TOKEN;

  // The production regression: no env credentials, but a trusted request token.
  Object.defineProperty(globalThis, contextSymbol, {
    configurable: true,
    value: { get: () => ({ headers: { "x-vercel-oidc-token": "test-request-oidc" } }) },
  });
  assert.equal(hasGatewayAuthentication(), true);
});
