export async function imageData(file?: File): Promise<string> {
  if (!file) return ''
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 200000) throw new Error('Elige una imagen PNG, JPEG o WebP de hasta 200 KB.')
  return await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsDataURL(file) })
}
