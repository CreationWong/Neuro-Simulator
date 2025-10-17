// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};

// 定义将返回给前端的视频信息结构
#[derive(Debug, Serialize, Deserialize, Clone)]
struct BilibiliVideoInfo {
    bvid: String,
    aid: u64,
}

// API响应的顶层结构
#[derive(Debug, Deserialize)]
struct BiliApiResponse {
    code: i32,
    message: String,
    data: Option<BiliApiData>,
}

// 'data' 结构，包含视频列表
#[derive(Debug, Deserialize)]
struct BiliApiData {
    archives: Vec<BilibiliVideoInfo>,
}

// Tauri命令，从前端调用
#[tauri::command]
async fn get_latest_replay_video() -> Result<BilibiliVideoInfo, String> {
    const MID: &str = "3546729368520811";
    const SERIES_ID: &str = "4281748"; // "直播回放" 的合集ID
    
    let url = format!(
        "https://api.bilibili.com/x/series/archives?mid={}&series_id={}&ps=1&pn=1",
        MID, SERIES_ID
    );

    let client = reqwest::Client::new();
    let response = client
        .get(&url)
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        .header("Referer", "https://space.bilibili.com/")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if !response.status().is_success() {
        return Err(format!("Bilibili API request failed with status: {}", response.status()));
    }

    let api_response: BiliApiResponse = response.json().await.map_err(|e| e.to_string())?;

    if api_response.code != 0 {
        return Err(format!("Bilibili API error: {}", api_response.message));
    }

    if let Some(data) = api_response.data {
        if let Some(video) = data.archives.into_iter().next() {
            return Ok(video);
        }
    }

    Err("No matching video found in Bilibili API response.".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .invoke_handler(tauri::generate_handler![get_latest_replay_video])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}