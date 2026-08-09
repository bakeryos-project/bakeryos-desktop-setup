pkgname=bakeryos-desktop-setup
pkgver=1.0.1
pkgrel=1
pkgdesc="Comprehensive desktop environment configuration package designed to provision a customized, highly productive, and visually polished user workspace with pre-configured settings, themes, and essential utilities."
arch=('any')
url="https://github.com/bakeryos-project/bakeryos-desktop-setup"
license=("GPL-3.0-or-later")
source=()
sha256sums=()
options=(!debug !strip)
depends=('pacman')
makedepends=('python' 'python-pip')

build(){
     cd $startdir
     python ./src/main.py
}

package() {
    install -d "${pkgdir}/etc/dconf/db/local.d"
    install -d "${pkgdir}/usr/share/gnome-shell/extensions"
    cp -r "${srcdir}/dconf/"* "${pkgdir}/etc/dconf/db/local.d/"
    cp -r "${startdir}/build/extensions/"* "${pkgdir}/usr/share/gnome-shell/extensions"

    install -Dm644 "${startdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
