import Dexie, { type Table } from "dexie";

export interface OfflineReading {
  id: string;
  pond_id: string;
  timestamp: string;
  temperature?: number;
  ph?: number;
  dissolved_oxygen?: number;
  turbidity?: number;
  conductivity?: number;
  ammonia?: number;
  synced: boolean;
  is_simulated?: boolean;
}

export interface OfflineDailyCheck {
  id: string;
  pond_id: string;
  timestamp: string;
  feeding: "normal" | "less" | "none";
  behavior: "normal" | "gasping" | "slow" | "at_surface";
  dead_fish_count: number;
  notes?: string;
  synced: boolean;
}

export class PondDatabase extends Dexie {
  readings!: Table<OfflineReading, string>;
  dailyChecks!: Table<OfflineDailyCheck, string>;

  constructor() {
    super("PondHealthAlertDB");
    this.version(1).stores({
      readings: "id, pond_id, timestamp, synced",
      dailyChecks: "id, pond_id, timestamp, synced",
    });
  }
}

export const db = new PondDatabase();
