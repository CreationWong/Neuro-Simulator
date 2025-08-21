import { invoke as tauriInvoke } from '@tauri-apps/api/core';

const IS_TAURI = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

// 与 ainst.rs 中的结构匹配
export interface BilibiliVideoInfo {
  bvid: string;
  aid: number;
}

const MID = '3546729368520811';
const SERIES_ID = '4281748'; // "直播回放" 的合集ID

/**
 * 获取最新的直播回放视频信息。
 * 此版本在Tauri和Web环境中均可运行。
 */
export async function getLatestReplayVideo(): Promise<BilibiliVideoInfo | null> {
  try {
    if (IS_TAURI) {
      console.log("Running in Tauri, invoking 'get_latest_replay_video' command...");
      return await tauriInvoke('get_latest_replay_video');
    } else {
      console.log("Running in Web, fetching from proxy...");
      const apiUrl = `/bilibili-api/x/series/archives?mid=${MID}&series_id=${SERIES_ID}&ps=1&pn=1`;
      
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch from proxy: ${response.statusText}`);
      }
      const data = await response.json();

      if (data.code !== 0) {
        throw new Error(`Bilibili API error: ${data.message}`);
      }

      const video = data?.data?.archives?.[0];
      if (video && video.bvid && video.aid) {
        return video;
      } else {
        throw new Error('No matching video found in API response.');
      }
    }
  } catch (error) {
    console.error('Failed to get latest replay video:', error);
    return null;
  }
}

/**
 * 根据视频信息构建iframe的URL。
 */
export function buildBilibiliIframeUrl(videoInfo: BilibiliVideoInfo): string {
  const baseUrl = '//www.bilibili.com/blackboard/html5mobileplayer.html';
  const params = new URLSearchParams({
    bvid: videoInfo.bvid,
    aid: String(videoInfo.aid),
    p: '1', // 明确指定播放第一P
    autoplay: '1',
    danmaku: '0',
    hasMuteButton: '1',
    hideCoverInfo: '0',
    fjw: '0',
    high_quality: '1',
  });
  return `${baseUrl}?${params.toString()}`;
}