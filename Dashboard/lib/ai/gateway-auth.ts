import { getVercelOidcTokenSync } from "@vercel/oidc";

export function hasGatewayAuthentication() {
  if (process.env.AI_GATEWAY_API_KEY?.trim()) return true;

  try {
    // Deployed functions receive OIDC through the trusted request context.
    return Boolean(getVercelOidcTokenSync()?.trim());
  } catch {
    return false;
  }
}
