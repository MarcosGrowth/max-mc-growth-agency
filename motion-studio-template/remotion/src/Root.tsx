import { Composition } from "remotion";
import { Tarjeta, tarjetaSchema } from "./components/Tarjeta";

// Registrar acá las piezas de cada reel (una carpeta por reel en src/, por ejemplo src/reel1/).
// Render transparente: npx remotion render <Id> salida.webm --codec=vp9 --image-format=png --pixel-format=yuva420p
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Tarjeta" component={Tarjeta} schema={tarjetaSchema}
      defaultProps={{ titulo: "Ejemplo", items: ["Primer punto", "Segundo punto", "Tercer punto"] }}
      durationInFrames={90} fps={30} width={1080} height={1920} />
  </>
);
