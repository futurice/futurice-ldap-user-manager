# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "ubuntu/trusty64"

  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  config.vm.network "forwarded_port", guest: 8000, host: 8008

  config.vm.provision "shell", path: "vagrant/provision-root.sh"
  config.vm.provision "shell", privileged: false,
    path: "vagrant/provision-user.sh"

  config.vm.provision "shell", run: "always", path: "vagrant/always-root.sh"
  config.vm.provision "shell", run: "always", privileged: false,
    path: "vagrant/always-user.sh"
end
