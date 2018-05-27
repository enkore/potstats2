export interface Stats {
  label: string,
  value: string,
}

export interface TopThread {
  tid: number,
  title: string,
  subtitle: string,
  thread_post_count: number,
}

export interface SeriesStats {
  name: string,
  value: string
  threads: TopThread[],
}

export interface MultiSeriesStat {
  name: string,
  series: SeriesStats[],
}

export interface User {
  name: string;
  uid: number;
}

export interface BoardStats {
  name: string,
  bid: number,
  description: string,
  thread_count: number,
  post_count: number
}

export interface PosterStats {
  User: User;
  uid: number;
  post_count: number;
  edit_count: number;
  avg_post_length:	number;
  threads_created:	number;
  quoted_count: number;
  quotes_count:	number;
}

export interface YearStats {
  year: number,
  post_count: number,
  edit_count: number,
  avg_post_length: number,
  threads_created: number,
  active_users: number,
}

export interface WeekdayStats {
  weekday: number,
  post_count: number,
  edit_count: number,
  avg_post_length: number,
  threads_created: number,
  active_users: number,
}

export interface HourlyStats {
  weekday_hour: string,
  post_count: number,
  edit_count: number,
  avg_post_length: number,
  threads_created: number,
  active_users: number,
}
