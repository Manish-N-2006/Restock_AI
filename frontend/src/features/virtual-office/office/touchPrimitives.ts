import { TOUCH_TAP_MAX_MOVE_PX } from './constants.js';

export function withinTapSlop(dx: number, dy: number): boolean {
  return Math.hypot(dx, dy) <= TOUCH_TAP_MAX_MOVE_PX;
}
