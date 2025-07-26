# =======================
#  main.py (단일 파일 버전)
# =======================
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    OrthographicLens, Vec2, Vec3, CardMaker, CollisionTraverser,
    CollisionNode, CollisionSphere, CollisionHandlerEvent, BitMask32,
    TransparencyAttrib, TextNode, LColor
)
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectWaitBar
from random import uniform, choice
import sys
import math
import time

# --------------------
#  설정/상수
# --------------------
SCREEN_HALF = 1.05          # 화면 경계(±1.0 조금 밖) … 좀비 스폰 반경
WORLD_SPEED = 1.0           # 전역 이동 속도 배율
BULLET_SPEED = 3.0
ZOMBIE_BASE_HP = 30
ZOMBIE_BASE_SPEED = 0.25
PLAYER_RADIUS = 0.08
ZOMBIE_RADIUS = 0.09
BULLET_RADIUS = 0.03
KILLS_PER_STAGE = 20
SHOOT_COOLDOWN = 0.2        # 초

# --------------------
#  헬퍼: 간단 스프라이트
# --------------------
def make_sprite(width=0.1, height=0.1, color=(1, 1, 1, 1)):
    cm = CardMaker('card')
    cm.setFrame(-width / 2, width / 2, -height / 2, height / 2)
    node = cm.generate()
    np = render2d.attachNewNode(node)
    np.setColor(LColor(*color))
    np.setTransparency(TransparencyAttrib.MAlpha)
    return np

# --------------------
#  게임 개체 클래스
# --------------------
class Bullet:
    def __init__(self, pos, direction, damage=10):
        self.node = make_sprite(0.04, 0.04, (1, 1, 0, 1))
        self.node.setPos(pos)
        self.dir = direction.normalized()
        self.damage = damage
        self.dead = False

    def update(self, dt):
        if self.dead:
            return
        self.node.setPos(self.node, self.dir.x * BULLET_SPEED * dt,
                         0, self.dir.y * BULLET_SPEED * dt)
        x, y, z = self.node.getPos()
        if abs(x) > SCREEN_HALF or abs(z) > SCREEN_HALF:
            self.destroy()

    def destroy(self):
        self.dead = True
        self.node.removeNode()


class Zombie:
    def __init__(self, stage):
        hp_scale = 1.0 + 0.2 * (stage - 1)
        speed_scale = 1.0 + 0.1 * (stage - 1)
        self.hp = int(ZOMBIE_BASE_HP * hp_scale)
        self.speed = ZOMBIE_BASE_SPEED * speed_scale
        self.node = make_sprite(0.12, 0.12, (0.3, 0.8, 0.3, 1))
        # 화면 바깥 랜덤 위치에서 생성
        edge = choice(['top', 'bottom', 'left', 'right'])
        if edge == 'top':
            x, z = uniform(-1.0, 1.0),  SCREEN_HALF
        elif edge == 'bottom':
            x, z = uniform(-1.0, 1.0), -SCREEN_HALF
        elif edge == 'left':
            x, z = -SCREEN_HALF, uniform(-1.0, 1.0)
        else:
            x, z =  SCREEN_HALF, uniform(-1.0, 1.0)
        self.node.setPos(x, 0, z)
        self.dead = False

    def update(self, dt, target_pos):
        if self.dead:
            return
        dx = target_pos.x - self.node.getX()
        dz = target_pos.y - self.node.getZ()
        dist = math.hypot(dx, dz)
        if dist > 0.001:
            vx = dx / dist * self.speed * dt
            vz = dz / dist * self.speed * dt
            self.node.setPos(self.node, vx, 0, vz)

    def hurt(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.destroy()

    def destroy(self):
        self.dead = True
        self.node.removeNode()


class Player:
    def __init__(self):
        self.node = make_sprite(0.1, 0.1, (0.2, 0.4, 1, 1))
        self.node.setPos(0, 0, 0)
        self.hp = 100
        self.max_hp = 100
        self.last_shot = 0.0

    def can_shoot(self):
        return (time.time() - self.last_shot) >= SHOOT_COOLDOWN

    def shoot(self):
        self.last_shot = time.time()

# --------------------
#  메인 게임 애플리케이션
# --------------------
class ZombieShooter(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()                 # 기본 마우스 카메라 조작 비활성
        self.setup_camera()                 # 직교 투영 설정

        # ECS 비슷하게 목록으로 관리
        self.player = Player()
        self.bullets = []
        self.zombies = []

        # HUD
        self.stage = 1
        self.kills = 0
        self.score_text = OnscreenText(
            text='Kills: 0  Stage: 1',
            pos=(-1.3, .9), scale=.05,
            align=TextNode.ALeft, fg=(1, 1, 1, 1))
        self.hp_bar = DirectWaitBar(
            value=self.player.hp, range=self.player.max_hp,
            pos=(0, 0, .85), barColor=(1, 0, 0, 1),
            frameSize=(-.5, .5, -.04, .04), scale=.8)

        # 입력
        self.accept('mouse1', self.on_mouse_click)

        # 주기 태스크
        self.taskMgr.add(self.update, 'gameUpdate')
        self.taskMgr.doMethodLater(2.0, self.spawn_zombie, 'spawner')

    # ---------------- Camera ----------------
    def setup_camera(self):
        lens = OrthographicLens()
        lens.setFilmSize(2, 2)  # (-1,1) 좌표계 화면에 딱 맞춤
        base.cam.node().setLens(lens)
        base.cam.setPos(0, -10, 0)          # 2D 평면을 정면에서 바라보게
        base.cam.lookAt(0, 0, 0)

    # ---------------- Input -----------------
    def on_mouse_click(self):
        if not base.mouseWatcherNode.hasMouse():
            return
        if not self.player.can_shoot():
            return
        mpos = base.mouseWatcherNode.getMouse()   # (-1~1, -1~1)
        dir_vec = Vec2(mpos.x, mpos.y) - Vec2(0, 0)
        if dir_vec.length() < 0.01:
            return
        bullet = Bullet(Vec3(0, 0, 0), dir_vec)
        self.bullets.append(bullet)
        self.player.shoot()

    # ---------------- Spawning --------------
    def spawn_zombie(self, task):
        self.zombies.append(Zombie(self.stage))
        spawn_interval = max(0.5, 2.0 - (self.stage * 0.1))  # 단계가 올라갈수록 빠르게
        return task.again + spawn_interval

    # ---------------- Main Loop -------------
    def update(self, task):
        dt = globalClock.getDt()

        # 플레이어는 이동하지 않지만 HP갱신
        self.hp_bar['value'] = self.player.hp

        # ---------------- Bullets ------------
        for bullet in self.bullets[:]:
            bullet.update(dt)
            if bullet.dead:
                self.bullets.remove(bullet)

        # ---------------- Zombies ------------
        player_pos2 = Vec2(self.player.node.getX(), self.player.node.getZ())
        for zombie in self.zombies[:]:
            zombie.update(dt, player_pos2)
            if zombie.dead:
                self.zombies.remove(zombie)
                continue

            # 충돌: 좀비 ↔ 플레이어
            dx = zombie.node.getX() - self.player.node.getX()
            dz = zombie.node.getZ() - self.player.node.getZ()
            if dx * dx + dz * dz <= (ZOMBIE_RADIUS + PLAYER_RADIUS) ** 2:
                self.player.hp -= 10
                zombie.destroy()
                if self.player.hp <= 0:
                    self.game_over()
                    return task.done

        # 충돌: 총알 ↔ 좀비
        for bullet in self.bullets[:]:
            if bullet.dead:
                continue
            bx, bz = bullet.node.getX(), bullet.node.getZ()
            for zombie in self.zombies[:]:
                dx = zombie.node.getX() - bx
                dz = zombie.node.getZ() - bz
                if dx * dx + dz * dz <= (BULLET_RADIUS + ZOMBIE_RADIUS) ** 2:
                    zombie.hurt(bullet.damage)
                    bullet.destroy()
                    self.bullets.remove(bullet)
                    if zombie.dead:
                        self.zombies.remove(zombie)
                        self.kills += 1
                        self.check_stage_up()
                    break  # bullet 소멸시 더 검사X

        return task.cont

    def check_stage_up(self):
        if self.kills and self.kills % KILLS_PER_STAGE == 0:
            self.stage += 1
        self.score_text.setText(f'Kills: {self.kills}  Stage: {self.stage}')

    # ---------------- GameOver --------------
    def game_over(self):
        OnscreenText(text='GAME OVER', pos=(0, 0), fg=(1, 0, 0, 1),
                     align=TextNode.ACenter, scale=.2, mayChange=False)
        # 모든 태스크 제거
        self.taskMgr.remove('spawner')

# ------------
#  실행
# ------------
if __name__ == '__main__':
    app = ZombieShooter()
    app.run()

