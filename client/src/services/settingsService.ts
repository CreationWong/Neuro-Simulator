
import { IS_TAURI } from '../utils/env';
import { LazyStore } from '@tauri-apps/plugin-store';
import type { AppSettings } from '../ui/settingsModal';

// Lazily initialize the store on first use to ensure the Tauri backend is ready.
let storeInstance: LazyStore | null = null;

function getStore(): LazyStore {
  if (!storeInstance) {
    console.log("Creating new LazyStore instance NOW.");
    storeInstance = new LazyStore('settings.json');
    console.log("LazyStore instance created:", storeInstance);
  }
  return storeInstance;
}

/**
 * Saves the application settings to the appropriate persistent storage.
 * Uses Tauri Store if in Tauri environment, otherwise falls back to localStorage.
 * @param settings - The settings object to save.
 */
export async function saveSettings(settings: AppSettings): Promise<void> {
  try {
    if (IS_TAURI) {
      const store = getStore();
      await store.set('neuro_settings', settings);
      await store.save(); // Persist the changes to disk
      console.log('Settings saved to Tauri Store.');
    } else {
      localStorage.setItem('neuro_settings', JSON.stringify(settings));
      console.log('Settings saved to localStorage.');
    }
  } catch (error) {
    console.error('Failed to save settings:', error);
  }
}

/**
 * Retrieves the application settings from the appropriate persistent storage.
 * Uses Tauri Store if in Tauri environment, otherwise falls back to localStorage.
 * @returns A promise that resolves to the AppSettings object or null if not found or on error.
 */
export async function getSettings(): Promise<AppSettings | null> {
  try {
    if (IS_TAURI) {
      const store = getStore();
      console.log('Attempting to load settings from Tauri Store.');
      const settings = await store.get<AppSettings>('neuro_settings');
      return settings ?? null; 
    } else {
      console.log('Attempting to load settings from localStorage.');
      const savedJson = localStorage.getItem('neuro_settings');
      if (savedJson) {
        return JSON.parse(savedJson) as AppSettings;
      }
      return null;
    }
  } catch (error) {
    console.error('Failed to retrieve settings:', error);
    return null;
  }
}
