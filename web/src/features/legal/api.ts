import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { LegalDocument } from '@/api/types';

export const legalKeys = {
  all: ['legal-versions'] as const,
  one: (document: LegalDocument, version: string) => ['legal-versions', document, version] as const,
};

export function useLegalVersions() {
  return useQuery({
    queryKey: legalKeys.all,
    queryFn: () => unwrap(api.GET('/api/v1/legal/versions')),
  });
}

export function useLegalVersion(document: LegalDocument, version: string | null) {
  return useQuery({
    queryKey: legalKeys.one(document, version ?? ''),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/legal/versions/{document}/{version}', {
          params: { path: { document, version: version ?? '' } },
        }),
      ),
    enabled: version != null,
  });
}
