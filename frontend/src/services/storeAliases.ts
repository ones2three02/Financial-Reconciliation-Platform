export interface StoreAliasIdentity {
  source_code: string;
  alias_name: string;
}

export interface QualityIssueIdentity {
  source_code: string;
  raw_value: string | null;
}

export const loadAllStoreAliases = async <T>(
  loadPage: (skip: number, limit: number) => Promise<T[]>,
  pageSize = 200,
): Promise<T[]> => {
  const aliases: T[] = [];
  let skip = 0;

  while (true) {
    const page = await loadPage(skip, pageSize);
    aliases.push(...page);
    if (page.length < pageSize) return aliases;
    skip += pageSize;
  }
};

export const findAliasForIssue = <T extends StoreAliasIdentity>(
  aliases: T[],
  issue: QualityIssueIdentity,
): T | undefined => {
  if (issue.raw_value === null) return undefined;
  return aliases.find(
    (alias) => alias.source_code === issue.source_code
      && alias.alias_name === issue.raw_value,
  );
};

export const canConfirmStoreAlias = (role: string | null | undefined) => role === 'admin';
