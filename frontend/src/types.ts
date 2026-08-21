export type ScreenType = 'telemetry' | 'diagnostics' | 'network' | 'archives' | 'terminal';

export interface CategoryData {
  id: string;
  name: string;
  count: number;
  max: number;
  percentage: number;
  color: 'primary' | 'secondary';
  gradient: string;
  activeNodes: number;
  errorRate: string;
  avgLatency: string;
  description: string;
}

export interface AnomalyItem {
  id: string;
  code: string;
  assetId: string;
  category: 'Sensors' | 'Optics' | 'Actuators' | 'Logic';
  title: string;
  severity: 'critical' | 'warning' | 'info';
  timestamp: string;
  metric: string;
  currentValue: string;
  expectedValue: string;
  status: 'pending' | 'triaged' | 'resolved' | 'quarantined';
  resolutionSuggestion: string;
}

export interface CatalogAsset {
  id: string;
  name: string;
  category: 'Sensors' | 'Optics' | 'Actuators' | 'Logic';
  specNumber: string;
  revision: string;
  health: number;
  status: 'optimal' | 'warning' | 'degraded' | 'offline';
  throughput: string;
  temperature: string;
  lastPing: string;
  drift: string;
}

export interface NetworkNode {
  id: string;
  name: string;
  type: 'gateway' | 'cluster' | 'sensor' | 'optics' | 'actuator' | 'logic';
  x: number;
  y: number;
  status: 'online' | 'warning' | 'offline';
  ip: string;
  ping: number;
  load: number;
  connections: string[];
}
