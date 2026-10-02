mkdir -p data/assets/icons/phosphor/2.1.1/bold

work_dir="$(mktemp -d)"

curl --fail --silent --show-error --location \
  https://registry.npmjs.org/@phosphor-icons/core/-/core-2.1.1.tgz \
  --output "$work_dir/core.tgz"

tar -xzf "$work_dir/core.tgz" -C "$work_dir"

icons=(
  users-three database gear-six list-checks asterisk
  folder-open sliders-horizontal lightning
  eye arrow-counter-clockwise arrows-left-right
  trend-up trend-down scales seal stamp
  cards-three tag-simple handshake hourglass-medium
  shield-check check-circle
)

for icon in "${icons[@]}"; do
  cp "$work_dir/package/assets/bold/${icon}-bold.svg" \
    data/assets/icons/phosphor/2.1.1/bold/
done

cp "$work_dir/package/LICENSE" \
  data/assets/icons/phosphor/LICENSE.phosphor.txt
