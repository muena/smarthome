# Changelog

## [1.0.0] - 2025-07-25

### Features
- Implemented full MQTT discovery for automatic Home Assistant integration
- Added smart command handling (ignores redundant open/close commands)
- Added stop command support with safety checks (only triggers when moving)
- Retained state publishing for correct HA state after restarts
- Automatic state synchronization on startup

### Refactor
- Unified logic for both garage doors into a single loop (removed redundant code)
- Optimized state publishing to send updates only on actual state changes (reduced MQTT traffic)

### Fixes
- Ignored retained MQTT commands to prevent unintended door movements after restart
- Removed retain flag from command topics to prevent accidental replay of last commands
