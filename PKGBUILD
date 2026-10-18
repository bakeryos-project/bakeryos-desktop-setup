pkgname=bakeryos-desktop-setup
pkgver=1.1.7
pkgrel=1
pkgdesc="Comprehensive desktop environment configuration package designed to provision a customized, highly productive, and visually polished user workspace with pre-configured settings, themes, and essential utilities."
arch=('any')
url="https://github.com/bakeryos-project/bakeryos-desktop-setup"
license=("GPL-3.0-or-later")
source=()
sha256sums=()
options=(!debug !strip)
depends=('pacman')
makedepends=('python' 'python-requests' 'unzip')
conflicts=('bakeryos-desktop-setup')
provides=('bakeryos-desktop-setup')
replaces=('bakeryos-desktop-setup')
backup=(
    'etc/dconf/db/local.d/01-gnome-setup'
    'etc/dconf/db/local.d/02-blur-my-shell'
    'etc/dconf/db/local.d/03-dash-to-panel'
    'etc/dconf/db/local.d/04-arc-menu'
    'etc/dconf/db/local.d/05-gtk4-ding'
    'etc/dconf/db/local.d/06-clipboard-history'
    'etc/dconf/db/local.d/07-vitals'
    'etc/dconf/db/local.d/08-console'
)

build(){
    cd $srcdir
    python ./gnome.py "$startdir/extensions" --shell-version 51
}

package() {
    local ext_dir="${pkgdir}/usr/share/gnome-shell/extensions"
    install -d "$ext_dir"
    for ext in "${startdir}/extensions/extract/"*; do
        if [ -d "$ext" ]; then
            cp -a "$ext" "$ext_dir/"
        fi
    done

    local dconf_dir="${pkgdir}/etc/dconf/db/local.d"
    install -d "$dconf_dir"

    if [ -d "${srcdir}/dconf" ]; then
        for file in "${srcdir}/dconf/"*; do
            if [ -f "$file" ]; then
                install -Dm644 "$file" "${dconf_dir}/$(basename "$file")"
            fi
        done
    fi

    install -Dm644 "${startdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
