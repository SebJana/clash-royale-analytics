import { Button, CircularProgress, type ButtonProps } from "@mui/material";
import { ArrowRight, RotateCcw } from "lucide-react";
import "./authOutcome.css";

type AuthActionButtonProps = Omit<
  ButtonProps,
  "action" | "variant" | "startIcon" | "endIcon" | "color"
> & {
  readonly action: "continue" | "retry";
  readonly busy?: boolean;
  readonly showIcon?: boolean;
};

// Use the same action styles across games and recovery menus. Continue points
// forward after the label; retry has an action icon before it. Final submission
// can hide the icon because it doesn't move to another challenge.
export function AuthActionButton({
  action,
  busy = false,
  showIcon = true,
  className = "",
  disabled,
  children,
  ...props
}: AuthActionButtonProps) {
  return (
    <Button
      {...props}
      variant={action === "continue" ? "contained" : "outlined"}
      disableElevation
      className={`auth-action-button is-${action} ${className}`}
      disabled={disabled || busy}
      aria-busy={busy}
      startIcon={
        busy ? (
          <CircularProgress size={18} color="inherit" />
        ) : showIcon && action === "retry" ? (
          <RotateCcw size={18} aria-hidden="true" />
        ) : undefined
      }
      endIcon={
        !busy && showIcon && action === "continue" ? (
          <ArrowRight size={18} aria-hidden="true" />
        ) : undefined
      }
    >
      {children ?? (action === "continue" ? "Continue" : "Try Again")}
    </Button>
  );
}
