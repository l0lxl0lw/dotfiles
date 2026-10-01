;; Starter configuration, copied (not linked) to ~/.spacemacs by deploy.sh.
(defun dotspacemacs/layers ()
  (setq-default
   dotspacemacs-distribution 'spacemacs
   dotspacemacs-configuration-layers '(org treemacs shell)
   dotspacemacs-install-packages 'used-only))

(defun dotspacemacs/init ()
  (setq-default
   dotspacemacs-editing-style 'vim
   dotspacemacs-line-numbers t
   dotspacemacs-auto-resume-layouts t))

(defun dotspacemacs/user-init ())
(defun dotspacemacs/user-config ()
  (setq shell-default-term-shell "/bin/zsh")
  (load (expand-file-name "~/dotfiles/emacs/main.el"))
  (load (expand-file-name "~/dotfiles/emacs/org-main.el"))
  ;; Add your own agenda paths before loading org-agenda.el.
  (load (expand-file-name "~/dotfiles/emacs/org-agenda.el"))
  (setq treemacs-show-hidden-files nil))
