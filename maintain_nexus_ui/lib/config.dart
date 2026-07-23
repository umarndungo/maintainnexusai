/// App configuration values used by the MaintainNexus Flutter dashboard.
///
/// The backend URL is provided at build time via `--dart-define`.
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);
