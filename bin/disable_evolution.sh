set -x
for filename in /usr/share/glib-2.0/schemas/org.gnome.[Ee]volution*; do
    echo > $filename
done

echo "Restore files using: dnf install --reinstall evolution-data-server (or something like that)"
