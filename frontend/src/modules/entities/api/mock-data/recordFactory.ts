import type { EntityRecord, EntitySeed } from "./types";

export function createEntityRecord(seed: EntitySeed): EntityRecord {
  const coverUrl = seed.coverUrl ?? "/images/history/mountains.jpg";
  const sourceId = `source-${seed.slug}`;
  return {
    details: {
      id: seed.id,
      type: seed.type,
      slug: seed.slug,
      title: { ru: seed.title, ce: null },
      shortDescription: { ru: seed.shortDescription, ce: null },
      fullDescription: { ru: seed.fullDescription, ce: null },
      coordinates: seed.coordinates,
      periodFrom: seed.periodFrom,
      periodTo: seed.periodTo ?? null,
      coverUrl,
      counts: { relations: seed.relations, sources: 1, media: 1 },
      status: "published",
      researchStatus: "verified",
    },
    sources: [
      {
        id: sourceId,
        title: seed.sourceTitle,
        type: seed.sourceType ?? "museum_material",
        author: "Редакция исторического атласа",
        publisher: null,
        publicationYear: null,
        url: null,
        archiveReference: `MOCK-${seed.id.slice(-3)}`,
        description: `Опубликованное описание и материалы к карточке «${seed.title}».`,
        verificationStatus: "contextual",
      },
    ],
    media: [
      {
        id: `media-${seed.slug}`,
        publicUrl: coverUrl,
        previewUrl: coverUrl,
        mimeType: "image/jpeg",
        width: seed.mediaWidth ?? 960,
        height: seed.mediaHeight ?? 640,
        caption: `Иллюстрация к карточке «${seed.title}»`,
        author: null,
        approximateDate: null,
        sourceDescription: seed.sourceTitle,
      },
    ],
  };
}
