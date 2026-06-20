import "@testing-library/jest-dom"
import { vi } from "vitest"

// jsdom does not implement HTMLDialogElement.prototype.showModal/close
HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
  this.setAttribute("open", "")
})
HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
  this.removeAttribute("open")
})
