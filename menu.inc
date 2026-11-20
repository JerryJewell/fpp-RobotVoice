<?php
// One FPP menu entry under Status/Control. No FPP playlists are used.
$menuEntries = array(array(
  'text' => 'Robot Voice',
  'type' => 'status',
  'page' => 'control.php',
  'wrap' => 1
));
foreach ($menuEntries as $entry) {
  if ($entry['type'] !== $menu) { continue; }
  printf("<li><a href='plugin.php?plugin=%s&amp;page=%s'>%s</a></li>\n",
         htmlspecialchars($plugin, ENT_QUOTES, 'UTF-8'),
         htmlspecialchars($entry['page'], ENT_QUOTES, 'UTF-8'),
         htmlspecialchars($entry['text'], ENT_QUOTES, 'UTF-8'));
}
?>
