class LocalMachineConfig:
  def __init__(self):
        self.ripgrep = True # Is ripgrep installed?
        self.OS = "Windows" if 'win' in platform else "Linux" if 'linux' in platform else "Mac" 
        # Other fields could include: processor type, available memory etc.
