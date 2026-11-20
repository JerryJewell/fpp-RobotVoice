<?php
// Same-origin control for the plugin. FPP's LAN authentication policy applies.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
function rv_reply($value, $code = 200) {
 http_response_code($code);
 echo json_encode($value, JSON_INVALID_UTF8_SUBSTITUTE);
 exit;
}
function rv_read($path) {
 $raw = is_file($path) ? @file_get_contents($path) : false;
 $data = $raw === false ? null : json_decode($raw, true);
 return is_array($data) ? $data : array();
}
function rv_atomic_write($path, $data) {
 $tmp = @tempnam(dirname($path), 'rv-');
 if ($tmp === false) return false;
 $json = json_encode($data, JSON_PRETTY_PRINT | JSON_INVALID_UTF8_SUBSTITUTE);
 $ok = $json !== false && @file_put_contents($tmp, $json . "\n") !== false &&
       @chmod($tmp, 0644) && @rename($tmp, $path);
 if (!$ok) @unlink($tmp);
 return $ok;
}
$base = isset($mediaDirectory) ? rtrim($mediaDirectory, '/') : '/home/fpp/media';
$dir = $base . '/plugindata/fpp-RobotVoice';
$boot = trim((string) @file_get_contents('/proc/sys/kernel/random/boot_id'));
$config = rv_read($dir . '/config.json');
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
 // A browser cannot send this custom header cross-origin without CORS.
 if (($_SERVER['HTTP_X_ROBOTVOICE_CONTROL'] ?? '') !== '1')
   rv_reply(array('error' => 'Invalid control request.'), 403);
 $action = $_POST['action'] ?? '';
 if ($action === 'on' || $action === 'off') {
   if ($action === 'on' && (empty($config['input_device']) || empty($config['output_device'])))
     rv_reply(array('error' => 'Choose and save the microphone and amplifier devices first.'), 409);
   if ($boot === '' || !rv_atomic_write($dir . '/live.json', array('boot'=>$boot, 'on'=>$action === 'on')))
     rv_reply(array('error' => 'Could not save the live switch.'), 500);
 } else {
   rv_reply(array('error' => 'Unknown control action.'), 400);
 }
} elseif (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
 rv_reply(array('error' => 'Method not allowed.'), 405);
}
$live = rv_read($dir . '/live.json');
$active = $boot !== '' && ($live['boot'] ?? '') === $boot && is_bool($live['on'] ?? null);
$on = $active ? $live['on'] : (($config['enabled'] ?? false) === true);
$status = rv_read($dir . '/status.json');
$fresh = abs(time() - (int) ($status['time'] ?? 0)) <= 35;
rv_reply(array('on'=>$on, 'engine'=>$fresh ? ($status['state'] ?? 'unknown') : 'not responding',
 'detail'=>$fresh ? ($status['error'] ?? '') : ''));
