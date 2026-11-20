<?php
// Local-only FPP plugin configuration page. FPP's parent page supplies its UI.
// FPP does not authenticate the LAN web UI by default: keep the Pi on a trusted LAN.
$baseMedia = isset($mediaDirectory) ? rtrim($mediaDirectory, '/') : '/home/fpp/media';
$dataDir = $baseMedia . '/plugindata/fpp-RobotVoice';
$configPath = $dataDir . '/config.json';
$statusPath = $dataDir . '/status.json';
$defaults = array(
 'enabled'=>false, 'input_device'=>'', 'output_device'=>'',
 'sample_rate'=>48000, 'blocksize'=>256, 'preset'=>'clean',
 'mic_gain'=>1.0, 'output_gain'=>0.30, 'noise_gate'=>0.02,
 'pitch_ratio'=>1.0, 'metallic'=>0.0, 'metallic_hz'=>65.0,
 'distortion'=>0.0, 'echo_ms'=>0
);
$profiles = array(
 'clean'=>array('pitch_ratio'=>1.00,'metallic'=>0.00,'metallic_hz'=>65,'distortion'=>0.00,'echo_ms'=>0),
 'classic'=>array('pitch_ratio'=>0.95,'metallic'=>0.52,'metallic_hz'=>68,'distortion'=>0.13,'echo_ms'=>0),
 'deep'=>array('pitch_ratio'=>0.72,'metallic'=>0.20,'metallic_hz'=>45,'distortion'=>0.23,'echo_ms'=>0),
 'dalek'=>array('pitch_ratio'=>0.88,'metallic'=>0.76,'metallic_hz'=>89,'distortion'=>0.35,'echo_ms'=>58)
);
function rv_escape($value) {
 return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function rv_read_json($path) {
 if (!is_readable($path)) return array();
 $data = json_decode((string)file_get_contents($path), true);
 return is_array($data) ? $data : array();
}
function rv_num($value, $default, $lo, $hi) {
 if (!is_scalar($value) || !is_numeric((string)$value)) return $default;
 $number = (float)$value;
 if (!is_finite($number)) return $default;
 return max($lo, min($hi, $number));
}
$message = '';
$config = array_replace($defaults, rv_read_json($configPath));
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
 // Whitelist keys and values. No arbitrary commands or paths from the browser.
 $new = $defaults;
 $new['enabled'] = isset($_POST['enabled']) && $_POST['enabled'] === '1';
 foreach (array('input_device','output_device') as $key) {
   $value = isset($_POST[$key]) && is_string($_POST[$key]) ? $_POST[$key] : '';
   $new[$key] = substr(trim($value), 0, 120);
 }
 $new['preset'] = isset($profiles[$_POST['preset'] ?? '']) ? $_POST['preset'] : 'clean';
 $new['sample_rate'] = ($_POST['sample_rate'] ?? '') == '44100' ? 44100 : 48000;
 $new['blocksize'] = ($_POST['blocksize'] ?? '') == '512' ? 512 : 256;
 foreach (array(
   'mic_gain'=>array(0,4), 'output_gain'=>array(0,1),
   'noise_gate'=>array(0,.10), 'pitch_ratio'=>array(.60,1.30),
   'metallic'=>array(0,1), 'metallic_hz'=>array(20,180),
   'distortion'=>array(0,1), 'echo_ms'=>array(0,200)
 ) as $key=>$bounds) {
   $new[$key] = rv_num($_POST[$key] ?? null, $defaults[$key], $bounds[0], $bounds[1]);
 }
 if (isset($_POST['apply_preset'])) {
   $new = array_replace($new, $profiles[$new['preset']]);
 }
 $new['echo_ms'] = (int)$new['echo_ms'];
 $json = json_encode($new, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
 $temporary = $configPath . '.webtmp';
 if (is_dir($dataDir) && file_put_contents($temporary, $json, LOCK_EX) !== false && rename($temporary, $configPath)) {
   $config = $new;
   $message = 'Saved. The audio engine reads changes automatically (normally within 1–3 seconds).';
 } else {
   $message = 'ERROR: Could not save. Check service install and write permissions on ' . $dataDir;
 }
}
$status = rv_read_json($statusPath);
$when = isset($status['time']) ? (time() - (int)$status['time']) : 999999;
$state = $when > 35 ? 'not responding (status stale)' : ($status['state'] ?? 'unknown');
$devices = isset($status['devices']) && is_array($status['devices']) ? $status['devices'] : array();
?>
<div class="container-fluid">
 <h2>Robot Voice — dedicated microphone effects</h2>
 <p>External microphone → USB audio adapter → Raspberry Pi (FPP) → USB adapter's 3.5 mm output → external amplifier. The software supplies neither the microphone nor the amplifier.</p>
 <p><strong>Engine:</strong> <?= rv_escape($state) ?>. <strong>Dropouts:</strong> <?= rv_escape($status['xruns'] ?? 'unknown') ?>. <strong>DSP errors:</strong> <?= rv_escape($status['processing_errors'] ?? 'unknown') ?>.</p>
 <?php if (!empty($status['error'])): ?><div class="alert alert-warning"><?= rv_escape($status['error']) ?></div><?php endif; ?>
 <?php if ($message !== ''): ?><div class="alert alert-info"><?= rv_escape($message) ?></div><?php endif; ?>
 <p>For safety, leave <b>Enable live microphone</b> unchecked until the microphone and amplifier are connected and the amplifier volume is low. No show or playlist is required.</p>
 <form method="post" action="plugin.php?plugin=fpp-RobotVoice&amp;page=control.php">
  <div class="form-group"><label><input type="checkbox" name="enabled" value="1" <?= !empty($config['enabled']) ? 'checked' : '' ?>> <strong>Enable live microphone processing (also after boot)</strong></label></div>
  <div class="form-group"><label for="input_device">Input device name (microphone)</label>
   <input class="form-control" id="input_device" name="input_device" list="rv_inputs" value="<?= rv_escape($config['input_device']) ?>" placeholder="Choose/copy device name below">
   <datalist id="rv_inputs"><?php foreach($devices as $device) if (!empty($device['input'])): ?><option value="<?= rv_escape($device['name']) ?>"><?= rv_escape($device['hostapi']) ?></option><?php endif; ?></datalist>
  </div>
  <div class="form-group"><label for="output_device">Output device name (amplifier)</label>
   <input class="form-control" id="output_device" name="output_device" list="rv_outputs" value="<?= rv_escape($config['output_device']) ?>" placeholder="Choose/copy device name below">
   <datalist id="rv_outputs"><?php foreach($devices as $device) if (!empty($device['output'])): ?><option value="<?= rv_escape($device['name']) ?>"><?= rv_escape($device['hostapi']) ?></option><?php endif; ?></datalist>
  </div>
  <div class="form-group"><label for="preset">Voice preset</label>
    <select class="form-control" id="preset" name="preset">
    <?php foreach (array('clean'=>'Clean / test', 'classic'=>'Classic robot', 'deep'=>'Deep robot', 'dalek'=>'Dalek-style') as $key=>$label): ?>
    <option value="<?= rv_escape($key) ?>" <?= $config['preset']===$key?'selected':'' ?>><?= rv_escape($label) ?></option><?php endforeach; ?>
    </select><small>Select a preset and click <b>Load preset values</b>, or edit the parameters manually below.</small>
  </div>
  <div class="form-group"><label>Sample rate</label><select class="form-control" name="sample_rate">
    <option value="48000" <?= $config['sample_rate']==48000?'selected':'' ?>>48 kHz</option><option value="44100" <?= $config['sample_rate']==44100?'selected':'' ?>>44.1 kHz</option></select></div>
  <div class="form-group"><label>Buffer</label><select class="form-control" name="blocksize">
    <option value="256" <?= $config['blocksize']==256?'selected':'' ?>>256 frames (lower latency)</option><option value="512" <?= $config['blocksize']==512?'selected':'' ?>>512 frames (fewer glitches)</option></select></div>
  <div class="row">
  <?php foreach (array(
  'mic_gain'=>array('Microphone gain',0,4,.05),
  'output_gain'=>array('Output level (start at 0.30)',0,1,.05),
  'noise_gate'=>array('Noise gate threshold',0,.10,.005),
  'pitch_ratio'=>array('Pitch ratio: below 1 is lower',.60,1.30,.01),
  'metallic'=>array('Metallic modulation',0,1,.01),
  'metallic_hz'=>array('Metallic frequency (Hz)',20,180,1),
  'distortion'=>array('Distortion',0,1,.01),
  'echo_ms'=>array('Echo milliseconds',0,200,1)
  ) as $field=>$desc): ?>
   <div class="col-sm-6 col-md-4"><div class="form-group"><label for="<?=rv_escape($field)?>"><?=rv_escape($desc[0])?></label>
   <input class="form-control" type="number" id="<?=rv_escape($field)?>" name="<?=rv_escape($field)?>" min="<?=$desc[1]?>" max="<?=$desc[2]?>" step="<?=$desc[3]?>" value="<?=rv_escape($config[$field])?>"></div></div>
  <?php endforeach; ?>
  </div>
  <button class="btn btn-primary" type="submit" name="save" value="1">Save settings</button>
  <button class="btn btn-secondary" type="submit" name="apply_preset" value="1">Load preset values and save</button>
 </form>
 <h3>Detected audio devices</h3>
 <p>Reload this page if you just plugged in the USB adapter. Names must be unique; if a sound device appears multiple times under ALSA, refer to the troubleshooting instructions.</p>
 <pre><?php if (!$devices) echo 'No audio devices reported yet. Check systemctl status fpp-robotvoice'; else foreach($devices as $device) echo rv_escape(sprintf('[%d] %s (%s) - %s%s', $device['index'], $device['name'], $device['hostapi'], $device['input']?'IN ':'', $device['output']?'OUT':'')) . "\n"; ?></pre>
 <p><small>Private to the local FPP installation. This page contains no audio recording feature. The FPP web interface itself may be accessible to other devices on your network.</small></p>
</div>
