// The 22 known locations the backend knows about. Coordinates and display
// names are duplicated here so the map can render pins without waiting on a
// tool call. The agent's tool calls are still the source of truth for which
// pins to show — this just lets us draw them with proper labels.

export type LocationId =
  | "tamaki-makaurau"
  | "waiheke"
  | "wai-o-tapu"
  | "tongariro-crossing"
  | "aoraki"
  | "hokitika"
  | "cape-reinga"
  | "milford-sound"
  | "waikato"
  | "taupo"
  | "tauranga"
  | "rotorua"
  | "whangarei"
  | "whakatane"
  | "whanganui"
  | "taranaki"
  | "otautahi"
  | "wellington"
  | "queenstown"
  | "dunedin"
  | "napier"
  | "nelson";

export interface LocationMeta {
  name: string;
  subtitle: string;
  lat: number;
  lng: number;
}

export const LOCATIONS: Record<LocationId, LocationMeta> = {
  "tamaki-makaurau": {
    name: "Tāmaki Makaurau",
    subtitle: "Auckland",
    lat: -36.8485,
    lng: 174.7633,
  },
  waiheke: {
    name: "Waiheke",
    subtitle: "Te Motu-arai-roa",
    lat: -36.8019,
    lng: 175.108,
  },
  "wai-o-tapu": {
    name: "Wai-O-Tapu",
    subtitle: "Sacred waters",
    lat: -38.3573,
    lng: 176.3686,
  },
  "tongariro-crossing": {
    name: "Tongariro",
    subtitle: "Alpine crossing",
    lat: -39.1328,
    lng: 175.6418,
  },
  aoraki: {
    name: "Aoraki",
    subtitle: "Mount Cook",
    lat: -43.595,
    lng: 170.1418,
  },
  hokitika: {
    name: "Hokitika",
    subtitle: "West Coast",
    lat: -42.7167,
    lng: 170.9667,
  },
  "cape-reinga": {
    name: "Cape Reinga",
    subtitle: "Te Rerenga Wairua",
    lat: -34.4287,
    lng: 172.6814,
  },
  "milford-sound": {
    name: "Milford Sound",
    subtitle: "Piopiotahi",
    lat: -44.6711,
    lng: 167.9244,
  },
  waikato: {
    name: "Waikato",
    subtitle: "Hamilton & the river",
    lat: -37.787,
    lng: 175.2793,
  },
  taupo: {
    name: "Taupō",
    subtitle: "Lake of Tia",
    lat: -38.6857,
    lng: 176.0702,
  },
  tauranga: {
    name: "Tauranga",
    subtitle: "Bay of Plenty",
    lat: -37.6878,
    lng: 176.1651,
  },
  rotorua: {
    name: "Rotorua",
    subtitle: "Geothermal heart",
    lat: -38.1368,
    lng: 176.2497,
  },
  whangarei: {
    name: "Whangārei",
    subtitle: "Northland",
    lat: -35.7269,
    lng: 174.3253,
  },
  whakatane: {
    name: "Whakatāne",
    subtitle: "Eastern Bay of Plenty",
    lat: -37.9582,
    lng: 176.9967,
  },
  whanganui: {
    name: "Whanganui",
    subtitle: "Te Awa Tupua",
    lat: -39.9301,
    lng: 175.0479,
  },
  taranaki: {
    name: "Taranaki",
    subtitle: "Mount Taranaki",
    lat: -39.2965,
    lng: 174.0644,
  },
  otautahi: {
    name: "Ōtautahi",
    subtitle: "Christchurch",
    lat: -43.532,
    lng: 172.6306,
  },
  wellington: {
    name: "Wellington",
    subtitle: "Te Whanganui-a-Tara",
    lat: -41.2865,
    lng: 174.7762,
  },
  queenstown: {
    name: "Queenstown",
    subtitle: "Tāhuna",
    lat: -45.0312,
    lng: 168.6626,
  },
  dunedin: {
    name: "Dunedin",
    subtitle: "Ōtepoti",
    lat: -45.8788,
    lng: 170.5028,
  },
  napier: {
    name: "Napier",
    subtitle: "Hawke's Bay",
    lat: -39.4928,
    lng: 176.912,
  },
  nelson: {
    name: "Nelson",
    subtitle: "Whakatū",
    lat: -41.2706,
    lng: 173.284,
  },
};

export const ALL_LOCATION_IDS = Object.keys(LOCATIONS) as LocationId[];
export const LOCATION_COUNT = ALL_LOCATION_IDS.length;

export function isLocationId(s: string): s is LocationId {
  return s in LOCATIONS;
}
