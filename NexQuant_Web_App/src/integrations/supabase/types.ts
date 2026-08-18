export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      app_versions: {
        Row: {
          changelog: string | null
          created_at: string
          download_url: string | null
          id: number
          is_mandatory: boolean
          version: string
        }
        Insert: {
          changelog?: string | null
          created_at?: string
          download_url?: string | null
          id?: number
          is_mandatory?: boolean
          version: string
        }
        Update: {
          changelog?: string | null
          created_at?: string
          download_url?: string | null
          id?: number
          is_mandatory?: boolean
          version?: string
        }
        Relationships: []
      }
      backtest_results: {
        Row: {
          created_at: string
          end_date: string
          final_balance: number
          id: string
          initial_balance: number
          max_drawdown: number
          net_profit: number
          profit_factor: number
          start_date: string
          strategy_config: Json
          symbol: string
          timeframe: string
          total_trades: number
          user_id: string
          win_rate: number
        }
        Insert: {
          created_at?: string
          end_date: string
          final_balance: number
          id?: string
          initial_balance: number
          max_drawdown: number
          net_profit: number
          profit_factor: number
          start_date: string
          strategy_config?: Json
          symbol: string
          timeframe: string
          total_trades: number
          user_id: string
          win_rate: number
        }
        Update: {
          created_at?: string
          end_date?: string
          final_balance?: number
          id?: string
          initial_balance?: number
          max_drawdown?: number
          net_profit?: number
          profit_factor?: number
          start_date?: string
          strategy_config?: Json
          symbol?: string
          timeframe?: string
          total_trades?: number
          user_id?: string
          win_rate?: number
        }
        Relationships: []
      }
      backtest_trades: {
        Row: {
          backtest_id: string
          created_at: string
          duration_minutes: number
          entry_price: number
          entry_time: string
          exit_price: number
          exit_time: string
          id: string
          pnl: number
          pnl_percent: number
          position_size: number
          side: string
          symbol: string
        }
        Insert: {
          backtest_id: string
          created_at?: string
          duration_minutes: number
          entry_price: number
          entry_time: string
          exit_price: number
          exit_time: string
          id?: string
          pnl: number
          pnl_percent: number
          position_size: number
          side: string
          symbol: string
        }
        Update: {
          backtest_id?: string
          created_at?: string
          duration_minutes?: number
          entry_price?: number
          entry_time?: string
          exit_price?: number
          exit_time?: string
          id?: string
          pnl?: number
          pnl_percent?: number
          position_size?: number
          side?: string
          symbol?: string
        }
        Relationships: [
          {
            foreignKeyName: "backtest_trades_backtest_id_fkey"
            columns: ["backtest_id"]
            isOneToOne: false
            referencedRelation: "backtest_results"
            referencedColumns: ["id"]
          },
        ]
      }
      bot_config: {
        Row: {
          is_running: boolean
          risk_pct: number
          score_min: number
          updated_at: string
          user_id: string
        }
        Insert: {
          is_running?: boolean
          risk_pct?: number
          score_min?: number
          updated_at?: string
          user_id: string
        }
        Update: {
          is_running?: boolean
          risk_pct?: number
          score_min?: number
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      bot_logs: {
        Row: {
          created_at: string
          id: number
          level: string
          message: string
          source: string | null
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: number
          level?: string
          message: string
          source?: string | null
          user_id: string
        }
        Update: {
          created_at?: string
          id?: number
          level?: string
          message?: string
          source?: string | null
          user_id?: string
        }
        Relationships: []
      }
      bot_status: {
        Row: {
          broker_type: string
          current_equity: number
          initial_equity: number
          is_running: boolean
          last_heartbeat: string | null
          started_at: string | null
          testnet: boolean
          updated_at: string
          user_id: string
        }
        Insert: {
          broker_type?: string
          current_equity?: number
          initial_equity?: number
          is_running?: boolean
          last_heartbeat?: string | null
          started_at?: string | null
          testnet?: boolean
          updated_at?: string
          user_id: string
        }
        Update: {
          broker_type?: string
          current_equity?: number
          initial_equity?: number
          is_running?: boolean
          last_heartbeat?: string | null
          started_at?: string | null
          testnet?: boolean
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      equity_snapshots: {
        Row: {
          drawdown: number
          equity: number
          id: number
          pnl_total: number
          ts: string
          user_id: string
        }
        Insert: {
          drawdown?: number
          equity: number
          id?: number
          pnl_total?: number
          ts?: string
          user_id: string
        }
        Update: {
          drawdown?: number
          equity?: number
          id?: number
          pnl_total?: number
          ts?: string
          user_id?: string
        }
        Relationships: []
      }
      market_regime: {
        Row: {
          confidence: number
          id: string
          news_sentiment: number
          nlp_signal: string | null
          regime: string
          symbol: string
          trend_direction: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          confidence?: number
          id?: string
          news_sentiment?: number
          nlp_signal?: string | null
          regime: string
          symbol: string
          trend_direction?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          confidence?: number
          id?: string
          news_sentiment?: number
          nlp_signal?: string | null
          regime?: string
          symbol?: string
          trend_direction?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      positions: {
        Row: {
          broker: string
          closed_at: string | null
          current_price: number
          entry_price: number
          id: string
          opened_at: string
          pnl: number
          pnl_pct: number
          qty: number
          side: string
          status: string
          symbol: string
          user_id: string
        }
        Insert: {
          broker?: string
          closed_at?: string | null
          current_price: number
          entry_price: number
          id?: string
          opened_at?: string
          pnl?: number
          pnl_pct?: number
          qty: number
          side: string
          status?: string
          symbol: string
          user_id: string
        }
        Update: {
          broker?: string
          closed_at?: string | null
          current_price?: number
          entry_price?: number
          id?: string
          opened_at?: string
          pnl?: number
          pnl_pct?: number
          qty?: number
          side?: string
          status?: string
          symbol?: string
          user_id?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          created_at: string
          display_name: string | null
          email: string | null
          id: string
          ingest_token: string
          role: string | null
          trial_end: string | null
        }
        Insert: {
          created_at?: string
          display_name?: string | null
          email?: string | null
          id: string
          ingest_token?: string
          role?: string | null
          trial_end?: string | null
        }
        Update: {
          created_at?: string
          display_name?: string | null
          email?: string | null
          id?: string
          ingest_token?: string
          role?: string | null
          trial_end?: string | null
        }
        Relationships: []
      }
      user_brokers: {
        Row: {
          asset_type: string
          broker_type: string
          created_at: string
          encrypted_api_key: string | null
          encrypted_api_secret: string | null
          id: string
          user_id: string
        }
        Insert: {
          asset_type: string
          broker_type: string
          created_at?: string
          encrypted_api_key?: string | null
          encrypted_api_secret?: string | null
          id?: string
          user_id: string
        }
        Update: {
          asset_type?: string
          broker_type?: string
          created_at?: string
          encrypted_api_key?: string | null
          encrypted_api_secret?: string | null
          id?: string
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      is_admin: { Args: never; Returns: boolean }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {},
  },
} as const
