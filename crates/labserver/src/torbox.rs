//! Fake TorBox web downloads (`webdl`) for `mdm-debrid` tests, as https://api-docs.torbox.app/
//! documents them (`{"success","error","detail","data"}`). Tokens `good` (premium) and `free`
//! (Bearer; `requestdl` takes `?token=`); each web download is ready after two `mylist` polls.

use std::collections::HashMap;
use std::sync::Mutex;

use axum::extract::{Path, Query};
use axum::http::{HeaderMap, StatusCode, header};
use axum::response::{IntoResponse, Response};
use bytes::Bytes;
use serde_json::{Value, json};

use crate::debrid::HOSTER;

/// A web download: (its polls so far, the file's size, name and direct link, the link it was
/// made from).
type Web = (u32, u64, String, String, String);
static TB_WEB: Mutex<Option<HashMap<u64, Web>>> = Mutex::new(None);
static NEXT: Mutex<u64> = Mutex::new(1);

fn form(body: &Bytes) -> Vec<(String, String)> {
    serde_urlencoded::from_bytes(body).unwrap_or_default()
}

fn field(f: &[(String, String)], name: &str) -> Option<String> {
    f.iter().find(|(k, _)| k == name).map(|(_, v)| v.clone())
}

fn tb_ok(data: Value) -> Response {
    axum::Json(json!({"success": true, "error": null, "detail": "lab", "data": data}))
        .into_response()
}

fn tb_error(status: StatusCode, code: &str) -> Response {
    (
        status,
        axum::Json(
            json!({"success": false, "error": code, "detail": format!("lab: {code}"), "data": null}),
        ),
    )
        .into_response()
}

/// As the documentation shows it: `ITEM_NOT_FOUND` with `success: true`.
fn tb_not_found() -> Response {
    (
        StatusCode::NOT_FOUND,
        axum::Json(
            json!({"success": true, "error": "ITEM_NOT_FOUND", "detail": "lab", "data": null}),
        ),
    )
        .into_response()
}

fn tb_token(t: &str) -> Option<bool> {
    match t {
        t if t == "good" || t.starts_with("good-") => Some(true),
        "free" => Some(false),
        _ => None,
    }
}

fn tb_premium(headers: &HeaderMap) -> Option<bool> {
    tb_token(
        headers
            .get(header::AUTHORIZATION)?
            .to_str()
            .ok()?
            .strip_prefix("Bearer ")?,
    )
}

fn tb_bad_token() -> Response {
    tb_error(StatusCode::FORBIDDEN, "BAD_TOKEN")
}

fn tb_next() -> u64 {
    let mut n = NEXT.lock().unwrap();
    *n += 1;
    *n
}

/// `GET /_debrid/webdl`: the ids the fake TorBox account still holds.
pub async fn held() -> Response {
    let ids: Vec<String> = TB_WEB
        .lock()
        .unwrap()
        .iter()
        .flat_map(|m| m.keys().map(u64::to_string))
        .collect();
    axum::Json(json!(ids)).into_response()
}

/// `GET /tb/v1/api/user/me`.
pub async fn tb_user(headers: HeaderMap) -> Response {
    let Some(premium) = tb_premium(&headers) else {
        return tb_bad_token();
    };
    let until = if premium {
        "2099-01-01T00:00:00Z"
    } else {
        "2020-01-01T00:00:00Z"
    };
    tb_ok(
        json!({"id": 1, "email": "lab@example.invalid", "plan": if premium { 2 } else { 0 },
        "is_subscribed": premium, "premium_expires_at": until}),
    )
}

static TB_DEVICE: Mutex<Option<HashMap<String, u32>>> = Mutex::new(None);

/// `GET /tb/v1/api/user/auth/device/start?app=` (public).
pub async fn tb_device_start() -> Response {
    let device = format!("tbdev{}", tb_next());
    TB_DEVICE
        .lock()
        .unwrap()
        .get_or_insert_with(HashMap::new)
        .insert(device.clone(), 0);
    tb_ok(
        json!({"device_code": device, "interval": 0, "expires_at": "2099-01-01T00:00:00Z",
        "verification_url": "https://torbox.app/oauth/device?app=MisterDownloadManager",
        "friendly_verification_url": "https://tor.box/link", "code": "123456"}),
    )
}

/// `POST /tb/v1/api/user/auth/device/token`, JSON `device_code`: allowed on the third poll,
/// then a premium token (`good-device`).
pub async fn tb_device_token(body: Bytes) -> Response {
    let v: Value = serde_json::from_slice(&body).unwrap_or(Value::Null);
    let device = v["device_code"].as_str().unwrap_or_default().to_owned();
    let mut all = TB_DEVICE.lock().unwrap();
    let Some(polls) = all.get_or_insert_with(HashMap::new).get_mut(&device) else {
        return tb_error(StatusCode::BAD_REQUEST, "ITEM_NOT_FOUND");
    };
    *polls += 1;
    if *polls < 3 {
        return tb_error(StatusCode::BAD_REQUEST, "DEVICE_CODE_NOT_USED");
    }
    tb_ok(json!({"access_token": "good-device", "token_type": "Bearer"}))
}

/// `GET /tb/v1/api/webdl/hosters` (public).
pub async fn tb_hosters() -> Response {
    tb_ok(
        json!([{"id": 1, "name": "Hostertest", "domains": [HOSTER, "hoster2.test"],
        "status": true, "type": "hoster"}]),
    )
}

/// `POST /tb/v1/api/webdl/createwebdownload` (`link`).
pub async fn tb_web_create(headers: HeaderMap, body: Bytes) -> Response {
    let Some(premium) = tb_premium(&headers) else {
        return tb_bad_token();
    };
    let Some(link) = field(&form(&body), "link").and_then(|l| url::Url::parse(&l).ok()) else {
        return tb_error(StatusCode::BAD_REQUEST, "INVALID_LINK");
    };
    let (size, name, direct) = match crate::debrid::direct_for(&headers, &link) {
        Ok(d) => d,
        Err("unsupported") => return tb_error(StatusCode::BAD_REQUEST, "UNSUPPORTED_SITE"),
        Err("down") => return tb_error(StatusCode::INTERNAL_SERVER_ERROR, "TEMPORARILY_DISABLED"),
        Err(_) => return tb_error(StatusCode::BAD_REQUEST, "LINK_OFFLINE"),
    };
    if !premium {
        return tb_error(StatusCode::FORBIDDEN, "PLAN_RESTRICTED_FEATURE");
    }
    let id = tb_next();
    TB_WEB
        .lock()
        .unwrap()
        .get_or_insert_with(HashMap::new)
        .insert(id, (0, size, name, direct, link.to_string()));
    tb_ok(json!({"hash": "h", "webdownload_id": id, "auth_id": "a"}))
}

/// One `mylist` entry: still at it for two polls, then finished with `files`.
fn tb_item(id: u64, name: &str, polls: u32, files: Vec<Value>) -> Value {
    let done = polls > 2;
    let state = if done { "completed" } else { "downloading" };
    json!({"id": id, "name": name, "download_state": state,
        "progress": if done { 1.0 } else { 0.5 }, "download_finished": done,
        "download_present": done, "error": null, "files": if done { files } else { vec![] }})
}

/// `GET /tb/v1/api/webdl/mylist?id=`.
pub async fn tb_list(
    headers: HeaderMap,
    Path(kind): Path<String>,
    Query(q): Query<HashMap<String, String>>,
) -> Response {
    if tb_premium(&headers).is_none() {
        return tb_bad_token();
    }
    if kind != "webdl" {
        return tb_not_found();
    }
    let id: u64 = q.get("id").and_then(|i| i.parse().ok()).unwrap_or(0);
    let mut all = TB_WEB.lock().unwrap();
    let all = all.get_or_insert_with(HashMap::new);
    if !q.contains_key("id") {
        if all.is_empty() {
            return tb_not_found();
        }
        let list: Vec<Value> = all
            .iter()
            .map(|(id, (polls, _, name, _, link))| {
                let mut v = tb_item(*id, name, *polls, vec![]);
                v["original_url"] = json!(link);
                v
            })
            .collect();
        return tb_ok(json!(list));
    }
    let Some((polls, size, name, _, _)) = all.get_mut(&id) else {
        return tb_not_found();
    };
    *polls += 1;
    let files = vec![json!({"id": 0, "name": name, "short_name": name, "size": size})];
    tb_ok(tb_item(id, name, *polls, files))
}

/// `GET /tb/v1/api/webdl/requestdl?token=&web_id=&file_id=&redirect=false`.
pub async fn tb_requestdl(
    Path(kind): Path<String>,
    Query(q): Query<HashMap<String, String>>,
) -> Response {
    if q.get("token").and_then(|t| tb_token(t)).is_none() {
        return tb_bad_token();
    }
    if kind != "webdl" {
        return tb_not_found();
    }
    if q.get("redirect").map(String::as_str) != Some("false") {
        return tb_error(StatusCode::BAD_REQUEST, "INVALID_OPTION");
    }
    let id: u64 = q.get("web_id").and_then(|i| i.parse().ok()).unwrap_or(0);
    let all = TB_WEB.lock().unwrap();
    match all.as_ref().and_then(|m| m.get(&id)) {
        Some((_, _, _, direct, _)) => tb_ok(json!(direct)),
        None => tb_not_found(),
    }
}

/// `POST /tb/v1/api/webdl/controlwebdownload`, JSON `{"webdl_id": id, "operation": "delete"}`.
pub async fn tb_control(headers: HeaderMap, body: Bytes) -> Response {
    if tb_premium(&headers).is_none() {
        return tb_bad_token();
    }
    let v: Value = serde_json::from_slice(&body).unwrap_or(Value::Null);
    if v["operation"] != "delete" {
        return tb_error(StatusCode::BAD_REQUEST, "INVALID_OPTION");
    }
    let Some(id) = v["webdl_id"].as_u64() else {
        return tb_error(StatusCode::BAD_REQUEST, "MISSING_REQUIRED_OPTION");
    };
    let web = TB_WEB
        .lock()
        .unwrap()
        .as_mut()
        .and_then(|m| m.remove(&id))
        .is_some();
    if web {
        tb_ok(Value::Null)
    } else {
        tb_not_found()
    }
}
