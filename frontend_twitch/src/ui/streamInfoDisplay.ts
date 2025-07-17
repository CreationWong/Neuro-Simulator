// src/ui/streamInfoDisplay.ts
import { StreamMetadataMessage } from '../types/common';

export class StreamInfoDisplay {
    private nicknameElement: HTMLElement;
    private titleElement: HTMLElement;
    private categoryElement: HTMLAnchorElement;
    private tagsContainer: HTMLDivElement;

    constructor() {
        this.nicknameElement = document.getElementById('streamer-nickname') as HTMLElement;
        this.titleElement = document.getElementById('stream-title-full') as HTMLElement;
        this.categoryElement = document.querySelector('.stream-category') as HTMLAnchorElement;
        this.tagsContainer = document.querySelector('.stream-tags') as HTMLDivElement;

        if (!this.nicknameElement || !this.titleElement || !this.categoryElement || !this.tagsContainer) {
            throw new Error("StreamInfoDisplay: One or more required elements not found in DOM!");
        }
        console.log("StreamInfoDisplay initialized.");
    }

    public update(data: StreamMetadataMessage): void {
        this.nicknameElement.textContent = data.streamer_nickname;
        this.titleElement.textContent = data.stream_title;
        this.categoryElement.textContent = data.stream_category;

        // 清空现有的标签
        this.tagsContainer.innerHTML = '';

        // 创建并添加新的标签
        data.stream_tags.forEach(tagText => {
            const tagElement = document.createElement('a');
            tagElement.href = '#'; // 链接可以为空
            tagElement.className = 'stream-tag';
            tagElement.textContent = tagText;
            this.tagsContainer.appendChild(tagElement);
        });

        console.log("Stream info display updated with new metadata.");
    }
}