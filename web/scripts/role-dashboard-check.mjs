// Read-only checks against the running app and its real backend; no API mocks.
import assert from "node:assert/strict";
const base = process.env.APP_URL ?? "http://localhost:3001";
const roles = {
  engineer: { path: "/dashboard", title: "Station Operations" },
  supervisor: { path: "/supervisor", title: "Maintenance Coordination" },
  executive: { path: "/executive", title: "Network Outcomes" },
};
async function page(path, cookie) {
  const response = await fetch(base + path, { headers: cookie ? { cookie } : {}, redirect: "manual" });
  return { response, html: await response.text() };
}
function redirected({ response, html }, target) {
  return response.headers.get("location")?.startsWith(target) || html.includes(`url=${target}`) || html.includes(`NEXT_REDIRECT;replace;${target}`);
}
for (const [role, { path, title }] of Object.entries(roles)) {
  const login = await fetch(base + "/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: `${role}-demo` }) });
  assert.equal(login.status, 200, `${role} login`);
  const cookie = login.headers.get("set-cookie")?.split(";")[0];
  assert.ok(cookie);
  try {
    const home = await page(path, cookie);
    assert.equal(home.response.status, 200);
    assert.ok(home.html.includes(`<h1>${title}</h1>`), `${role} page heading`);
    assert.ok(home.html.includes(`role-${role}`), `${role} visual theme`);
    if (role === "supervisor") {
      assert.ok(home.html.includes("Escalation desk") && home.html.includes("Approval desk"));
      assert.ok(redirected(await page("/dashboard", cookie), path));
    } else {
      assert.ok(redirected(await page("/supervisor", cookie), path));
    }
    if (role === "engineer") assert.ok(redirected(await page("/executive", cookie), path));
    if (role === "executive") {
      assert.ok(redirected(await page("/dashboard", cookie), path));
      assert.ok(!home.html.includes(">Approve &amp; dispatch</button>"));
    }
    console.log(`PASS ${role}: dashboard, theme and role redirects`);
  } finally {
    await fetch(base + "/api/auth/logout", { method: "POST", headers: { cookie } });
  }
}
assert.ok(redirected(await page("/supervisor"), "/login"));
console.log("PASS unauthenticated access redirects to login");
