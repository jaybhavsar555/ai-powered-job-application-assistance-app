(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/src/components/providers/Providers.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Providers",
    ()=>Providers
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$tanstack$2f$query$2d$core$2f$build$2f$modern$2f$queryClient$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/@tanstack/query-core/build/modern/queryClient.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$tanstack$2f$react$2d$query$2f$build$2f$modern$2f$QueryClientProvider$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/@tanstack/react-query/build/modern/QueryClientProvider.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next-themes/dist/index.mjs [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
function AuthBootstrap({ children }) {
    _s();
    const [ready, setReady] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AuthBootstrap.useEffect": ()=>{
            let done = false;
            const markReady = {
                "AuthBootstrap.useEffect.markReady": ()=>{
                    if (done) return;
                    done = true;
                    setReady(true);
                }
            }["AuthBootstrap.useEffect.markReady"];
            // Never block the UI if persist/API hangs (proxy to :8001, Strict Mode remount).
            const failOpen = window.setTimeout(markReady, 2_000);
            void ({
                "AuthBootstrap.useEffect": async ()=>{
                    try {
                        await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ensureValidSession"])();
                    } catch (e) {
                        console.warn('[AuthBootstrap] session check failed — is the API running?', e);
                    } finally{
                        window.clearTimeout(failOpen);
                        markReady();
                    }
                }
            })["AuthBootstrap.useEffect"]();
            return ({
                "AuthBootstrap.useEffect": ()=>{
                    window.clearTimeout(failOpen);
                }
            })["AuthBootstrap.useEffect"];
        }
    }["AuthBootstrap.useEffect"], []);
    if (!ready) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex h-screen w-full items-center justify-center bg-background text-muted-foreground text-sm",
            children: "Connecting to Career OS…"
        }, void 0, false, {
            fileName: "[project]/src/components/providers/Providers.tsx",
            lineNumber: 41,
            columnNumber: 7
        }, this);
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/providers/Providers.tsx",
        lineNumber: 47,
        columnNumber: 10
    }, this);
}
_s(AuthBootstrap, "KuazqYXqOk+6VRk8yHVvoClyoeE=");
_c = AuthBootstrap;
function Providers({ children, ...props }) {
    _s1();
    const [queryClient] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        "Providers.useState": ()=>new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$tanstack$2f$query$2d$core$2f$build$2f$modern$2f$queryClient$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["QueryClient"]({
                defaultOptions: {
                    queries: {
                        staleTime: 60 * 1000,
                        retry: 1
                    }
                }
            })
    }["Providers.useState"]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ThemeProvider"], {
        ...props,
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$tanstack$2f$react$2d$query$2f$build$2f$modern$2f$QueryClientProvider$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["QueryClientProvider"], {
            client: queryClient,
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(AuthBootstrap, {
                children: children
            }, void 0, false, {
                fileName: "[project]/src/components/providers/Providers.tsx",
                lineNumber: 63,
                columnNumber: 9
            }, this)
        }, void 0, false, {
            fileName: "[project]/src/components/providers/Providers.tsx",
            lineNumber: 62,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/src/components/providers/Providers.tsx",
        lineNumber: 61,
        columnNumber: 5
    }, this);
}
_s1(Providers, "QsgPpYeVmga53we4oMCsLJu5iQw=");
_c1 = Providers;
var _c, _c1;
__turbopack_context__.k.register(_c, "AuthBootstrap");
__turbopack_context__.k.register(_c1, "Providers");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/lib/api.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "API_BASE_URL",
    ()=>API_BASE_URL,
    "apiFetch",
    ()=>apiFetch,
    "authHeaders",
    ()=>authHeaders,
    "default",
    ()=>__TURBOPACK__default__export__,
    "ensureDemoAuth",
    ()=>ensureDemoAuth,
    "ensureValidSession",
    ()=>ensureValidSession,
    "getApiErrorMessage",
    ()=>getApiErrorMessage,
    "refreshSession",
    ()=>refreshSession
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/axios/lib/axios.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/store/auth.ts [app-client] (ecmascript)");
;
;
const API_BASE_URL = ("TURBOPACK compile-time value", "/api/v1") || '/api/v1';
const API_BASE = API_BASE_URL;
const AUTH_TIMEOUT_MS = 6_000;
const api = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].create({
    baseURL: API_BASE,
    timeout: 30_000,
    headers: {
        'Content-Type': 'application/json'
    }
});
function isAuthEndpoint(url) {
    if (!url) return false;
    return /\/auth\/(login|register|demo|me|credentials)/.test(url);
}
let sessionRefresh = null;
api.interceptors.request.use((config)=>{
    const token = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().token;
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
api.interceptors.response.use((response)=>response, async (error)=>{
    const status = error.response?.status;
    const original = error.config;
    if (status !== 401 || !original || original._retry || isAuthEndpoint(original.url)) {
        return Promise.reject(error);
    }
    original._retry = true;
    const nextToken = await refreshSession();
    if (!nextToken) {
        return Promise.reject(error);
    }
    original.headers = original.headers || {};
    original.headers.Authorization = `Bearer ${nextToken}`;
    return api.request(original);
});
function getApiErrorMessage(err, fallback = 'Request failed') {
    if (!err || typeof err !== 'object') return fallback;
    const anyErr = err;
    const detail = anyErr.response?.data?.detail;
    if (detail && /could not validate credentials/i.test(String(detail))) {
        return 'Session expired — sign in again (or wait a moment for a new demo session).';
    }
    if (detail) return String(detail);
    if (anyErr.response?.status === 401 || anyErr.response?.status === 403) {
        return 'Not authenticated — sign in again.';
    }
    if (anyErr.response?.status && anyErr.response.status >= 500) {
        return `API error ${anyErr.response.status} — check Docker backend on :8001`;
    }
    if (anyErr.message === 'Network Error' || anyErr.code === 'ERR_NETWORK') {
        return 'Cannot reach API — is Docker backend up? (docker compose up -d api)';
    }
    if (anyErr.message) return anyErr.message;
    return fallback;
}
function authHeaders() {
    const token = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().token;
    return token ? {
        Authorization: `Bearer ${token}`
    } : {};
}
async function applyTokenResponse(data) {
    const id = data.user_id || data.id || '';
    __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().setAuth(data.access_token, {
        id,
        email: data.email,
        role: data.role
    });
    return data.access_token;
}
async function ensureDemoAuth(force = false) {
    const existing = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().token;
    if (existing && !force) return existing;
    const { data } = await __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].post(`${API_BASE}/auth/demo`, null, {
        timeout: AUTH_TIMEOUT_MS
    });
    return applyTokenResponse(data);
}
async function tokenIsValid(token) {
    try {
        const { data } = await __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].get(`${API_BASE}/auth/me`, {
            headers: {
                Authorization: `Bearer ${token}`
            },
            timeout: AUTH_TIMEOUT_MS
        });
        __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().setAuth(token, {
            id: data.id,
            email: data.email,
            role: data.role
        });
        return true;
    } catch (err) {
        if (__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].isAxiosError(err) && err.response?.status === 401) {
            return false;
        }
        // Network / API down / timeout — keep the stored token; pages will show connection errors.
        return true;
    }
}
async function refreshSession() {
    if (!sessionRefresh) {
        sessionRefresh = (async ()=>{
            try {
                return await ensureDemoAuth(true);
            } catch  {
                __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().logout();
                return null;
            } finally{
                sessionRefresh = null;
            }
        })();
    }
    return sessionRefresh;
}
async function ensureValidSession() {
    await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["waitForAuthHydration"])();
    const token = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().token;
    if (token && await tokenIsValid(token)) {
        return token;
    }
    if (token) {
        __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().logout();
    }
    try {
        return await ensureDemoAuth(true);
    } catch  {
        return null;
    }
}
async function apiFetch(input, init = {}) {
    const headers = new Headers(init.headers);
    const token = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$store$2f$auth$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useAuthStore"].getState().token;
    if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    let res = await fetch(input, {
        ...init,
        headers
    });
    if (res.status === 401 && !isAuthEndpoint(input)) {
        const next = await refreshSession();
        if (next) {
            headers.set('Authorization', `Bearer ${next}`);
            res = await fetch(input, {
                ...init,
                headers
            });
        }
    }
    return res;
}
const __TURBOPACK__default__export__ = api;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/store/auth.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "useAuthStore",
    ()=>useAuthStore,
    "waitForAuthHydration",
    ()=>waitForAuthHydration
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zustand$2f$esm$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/zustand/esm/index.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zustand$2f$esm$2f$middleware$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/zustand/esm/middleware.mjs [app-client] (ecmascript)");
;
;
const useAuthStore = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zustand$2f$esm$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["create"])()((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zustand$2f$esm$2f$middleware$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["persist"])((set)=>({
        token: null,
        user: null,
        hasHydrated: false,
        setAuth: (token, user)=>set({
                token,
                user
            }),
        logout: ()=>set({
                token: null,
                user: null
            }),
        setHasHydrated: (value)=>set({
                hasHydrated: value
            })
    }), {
    name: 'auth-storage',
    partialize: (state)=>({
            token: state.token,
            user: state.user
        }),
    onRehydrateStorage: ()=>(state, error)=>{
            if (error) {
                console.warn('[auth] persist rehydrate failed', error);
            }
            // Always mark hydrated so bootstrap cannot wait forever.
            useAuthStore.getState().setHasHydrated(true);
            if (state) {
            // no-op: persist already merged token/user
            }
        }
}));
function alreadyHydrated() {
    return useAuthStore.getState().hasHydrated || Boolean(useAuthStore.persist?.hasHydrated?.());
}
function waitForAuthHydration(timeoutMs = 800) {
    if (alreadyHydrated()) {
        useAuthStore.getState().setHasHydrated(true);
        return Promise.resolve();
    }
    return new Promise((resolve)=>{
        let settled = false;
        const finish = ()=>{
            if (settled) return;
            settled = true;
            useAuthStore.getState().setHasHydrated(true);
            resolve();
        };
        const unsubFinish = useAuthStore.persist.onFinishHydration(()=>{
            unsubFinish();
            finish();
        });
        const unsubStore = useAuthStore.subscribe((s)=>{
            if (s.hasHydrated) {
                unsubStore();
                finish();
            }
        });
        // Race: hydration may complete between the first check and the listeners.
        if (alreadyHydrated()) {
            unsubFinish();
            unsubStore();
            finish();
            return;
        }
        window.setTimeout(()=>{
            unsubFinish();
            unsubStore();
            finish();
        }, timeoutMs);
    });
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=src_12sody6._.js.map