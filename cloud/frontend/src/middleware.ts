import { NextResponse, type NextRequest } from "next/server";

// Local mode: no authentication required
// All routes are publicly accessible
export async function middleware(request: NextRequest) {
  // No authentication checks in local mode
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static, _next/image (Next.js internals)
     * - favicon.ico, static assets (svg, png, jpg, etc.)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
