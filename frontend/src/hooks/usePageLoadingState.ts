import { useEffect, useState, useRef } from "react";

type UsePageLoadingStateOptions = {
  // Loading states from various data sources
  loadingStates: boolean[];

  // Error states from various data sources
  errorStates: boolean[];

  // Function to check if there's any data available
  // Returns true if data exists, false otherwise
  hasData: () => boolean;

  // Dependency that triggers a reset (e.g., playerTag)
  // When this changes, the loading state resets
  resetDependency?: string | number;

  // Minimum time to show loading spinner (default: 300ms)
  minDisplayTime?: number;

  // Maximum time to show loading spinner before giving up (default: 10000ms)
  maxLoadTime?: number;
};

type UsePageLoadingStateReturn = {
  // True during initial page load
  isInitialLoad: boolean;

  // True if any loading is happening
  isLoading: boolean;

  // True if any error occurred
  hasError: boolean;
};

/**
 * Custom hook to manage page loading states with smart timing logic
 *
 * This hook provides:
 * - Immediate page access (no blocking)
 * - Minimum spinner display time for better UX (if spinner/loading animation exists)
 * - Automatic reset when navigating between entities
 * - Fallback timeout to prevent infinite loading
 *
 * @param options Configuration options for the loading state
 * @returns Loading state information
 */
export function usePageLoadingState({
  loadingStates,
  errorStates,
  hasData,
  resetDependency,
  minDisplayTime = 300,
  // Maximum time to show loading spinner before giving up (default: 10000ms)
  maxLoadTime = 10000,
}: UsePageLoadingStateOptions): UsePageLoadingStateReturn {
  // Loading state: tracks initial page load to show spinner immediately
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // Track if there ever was data to differentiate between first load and subsequent loads
  const [hasEverHadData, setHasEverHadData] = useState(false);

  // Track if a loading cycle has completed (regardless of whether data was returned)
  const [hasCompletedFirstLoad, setHasCompletedFirstLoad] = useState(false);

  // Track component mount to ensure loading spinner shows immediately
  const isMountedRef = useRef(false);
  const loadStartTimeRef = useRef<number>(Date.now());
  const wasLoadingRef = useRef(false);

  // Computed loading and error states
  const isLoading = loadingStates.some((state) => state);
  const hasError = errorStates.some((state) => state);

  useEffect(() => {
    isMountedRef.current = true;
    loadStartTimeRef.current = Date.now();
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Track loading state changes to detect when a load cycle completes
  useEffect(() => {
    // If we were loading and now we're not, mark that a load cycle has completed
    if (wasLoadingRef.current && !isLoading) {
      setHasCompletedFirstLoad(true);
    }
    wasLoadingRef.current = isLoading;
  }, [isLoading]);

  // Clear initial load state once data is available or loading is complete
  useEffect(() => {
    // Mark that there is data if the hasData function returns true
    if (hasData() && !hasEverHadData) {
      setHasEverHadData(true);
    }

    // Only clear initial load state when:
    // 1. Page is not loading anymore AND
    // 2. There either is data OR there was data before OR there's an error OR a loading cycle completed (even with empty results) AND
    // 3. At least minDisplayTime has passed to ensure spinner is visible
    if (
      !isLoading &&
      (hasData() || hasEverHadData || hasError || hasCompletedFirstLoad)
    ) {
      const timeElapsed = Date.now() - loadStartTimeRef.current;

      if (timeElapsed >= minDisplayTime) {
        setIsInitialLoad(false);
      } else {
        // Wait for the minimum display time to remove spinner
        setTimeout(() => {
          if (isMountedRef.current) {
            setIsInitialLoad(false);
          }
        }, minDisplayTime - timeElapsed);
      }
    }
  }, [
    isLoading,
    hasData,
    hasEverHadData,
    hasError,
    hasCompletedFirstLoad,
    minDisplayTime,
  ]);

  // Reset initial load state when resetDependency changes (e.g., navigating to different player)
  useEffect(() => {
    if (resetDependency !== undefined) {
      setIsInitialLoad(true);
      setHasEverHadData(false);
      setHasCompletedFirstLoad(false);
      loadStartTimeRef.current = Date.now();
    }
  }, [resetDependency]);

  // Fallback timeout to ensure loading state doesn't persist indefinitely
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isInitialLoad && isMountedRef.current) {
        // Still display page even though it's not fully loaded yet
        setIsInitialLoad(false);
      }
    }, maxLoadTime);

    return () => clearTimeout(timeout);
  }, [isInitialLoad, maxLoadTime]);

  return {
    isInitialLoad,
    isLoading,
    hasError,
  };
}
