/**
 * Z-Index Design Tokens
 *
 * Layered stacking context for UI elements.
 * Named values prevent arbitrary z-index wars.
 *
 * Hierarchy:
 *   base < sticky < dropdown < overlay < modal < toast < tooltip
 */

module.exports = {
  auto: 'auto',
  base: '0',
  raised: '1',
  dropdown: '1000',
  sticky: '1020',
  fixed: '1030',
  overlay: '1040',
  modal: '1050',
  toast: '1060',
  tooltip: '1070',
  max: '9999',
};
