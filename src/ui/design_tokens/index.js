/**
 * Design Tokens Index
 *
 * Central export for all design token modules.
 * Imported by tailwind.config.js to extend the theme.
 */

const colors = require('./colors');
const spacing = require('./spacing');
const radius = require('./radius');
const shadows = require('./shadows');
const zIndex = require('./z_index');
const typography = require('./typography');
const animation = require('./animation');
const containers = require('./containers');

module.exports = {
  colors,
  spacing,
  borderRadius: radius,
  ...shadows,
  zIndex,
  ...typography,
  ...animation,
  ...containers,
};
