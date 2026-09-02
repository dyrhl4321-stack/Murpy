import WebKit

struct Cookie {
    var name: String
    var value: String
}

let gcmMessageIDKey = "00000000000" // update this with actual ID if using Firebase 

// URL for first launch
let rootUrl = URL(string: "https://murpy.app")!

// allowed origin is for what we are sticking to pwa domain
// This should also appear in Info.plist
let allowedOrigins: [String] = ["murpy.app"]

// auth origins will open in modal and show toolbar for back into the main origin.
// These should also appear in Info.plist
// ★9-02 비어 있었다 — 구글/카카오 로그인 창이 본창 웹뷰에서 열려 구글 정책(disallowed_useragent)에
//   막힐 수 있다. 로그인이 거쳐 가는 도메인 전부: 구글 · 카카오(인증/로그인) · 카카오 커스텀토큰
//   Worker · Firebase 인증 핸들러 · (준비) Sign in with Apple.
//   ※실기기에서 구글·카카오 로그인이 끝까지 되는지 반드시 확인 — 그래도 막히면
//     ASWebAuthenticationSession(사파리 창) 방식으로 바꿔야 한다.
let authOrigins: [String] = [
    "accounts.google.com",
    "kauth.kakao.com",
    "accounts.kakao.com",
    "murpy-kakao.dyrhl4321.workers.dev",
    "murpyprototype.firebaseapp.com",
    "appleid.apple.com",
]
// allowedOrigins + authOrigins <= 10

let platformCookie = Cookie(name: "app-platform", value: "iOS App Store")

// UI options
let displayMode = "standalone" // standalone / fullscreen.
let adaptiveUIStyle = true     // iOS 15+ only. Change app theme on the fly to dark/light related to WebView background color.
let overrideStatusBar = false   // iOS 13-14 only. if you don't support dark/light system theme.
let statusBarTheme = "dark"    // dark / light, related to override option.
let pullToRefresh = true    // Enable/disable pull down to refresh page
