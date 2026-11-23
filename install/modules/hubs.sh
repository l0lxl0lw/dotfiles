# Link every active hub into every installed tool, then let Orca add its own
# hooks and skills for the agents it detects.
install_component() {
  sync_hubs all
  orca_integrate
}
