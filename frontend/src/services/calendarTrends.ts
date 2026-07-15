export interface CalendarRange {
  startDate: string;
  endDate: string;
}

const sameRange = (
  left: CalendarRange,
  right: CalendarRange | null,
) => right !== null
  && left.startDate === right.startDate
  && left.endDate === right.endDate;

export const createLatestCalendarRangeLoader = <T>(
  loadRange: (range: CalendarRange) => Promise<T>,
) => {
  let latestRequestId = 0;

  return async (
    requestedRange: CalendarRange,
    getCurrentRange: () => CalendarRange | null,
  ): Promise<T | null> => {
    const requestId = ++latestRequestId;
    const result = await loadRange(requestedRange);
    if (
      requestId !== latestRequestId
      || !sameRange(requestedRange, getCurrentRange())
    ) {
      return null;
    }
    return result;
  };
};
