// src/lib/reactNativeAsyncStorageTypes.ts
export interface Persistence {
  readonly type: "SESSION" | "LOCAL" | "NONE" | "COOKIE";
}

export const enum PersistenceType {
  SESSION = "SESSION",
  LOCAL = "LOCAL",
  NONE = "NONE",
  COOKIE = "COOKIE",
}

export type PersistedBlob = Record<string, unknown>;
export type PersistenceValue = PersistedBlob | string;

export const STORAGE_AVAILABLE_KEY = "__sak";

export interface StorageEventListener {
  (value: PersistenceValue | null): void;
}

export interface PersistenceInternal extends Persistence {
  type: PersistenceType;
  _isAvailable(): Promise<boolean>;
  _set(key: string, value: PersistenceValue): Promise<void>;
  _get<T extends PersistenceValue>(key: string): Promise<T | null>;
  _remove(key: string): Promise<void>;
  _addListener(key: string, listener: StorageEventListener): void;
  _removeListener(key: string, listener: StorageEventListener): void;
  _shouldAllowMigration?: boolean;
}