import { NextResponse } from "next/server";
export async function GET() {
  return NextResponse.json({ ok:true, hasToken: !!process.env.GH_TOKEN, time: new Date().toISOString() });
}
